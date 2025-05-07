import sys
import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box, Point
from shapely.errors import GEOSException
import contextily as ctx
from pykml import parser
from lxml import etree
import ast
import warnings
import traceback
import re
import time

# --- ReportLab Imports ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter

# --- Pillow (PIL) Import for image dimensions ---
from PIL import Image as PILImage

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar, QTextEdit,
                             QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- Configuration ---
TERRITORY_NAME_INDEX = 1
TERRITORY_NUMBER_INDEX = 3
BOUNDARY_COLUMN_INDEX = 11
OUTPUT_FOLDER = "Generated_Maps_ReportLab_PDF_Corrected_GUI" # New name
MAP_IMAGE_DPI = 200
FIGURE_WIDTH_INCHES = 7.5
FIGURE_MAP_HEIGHT_INCHES = 6.0
BASEMAP_PROVIDER = ctx.providers.OpenStreetMap.Mapnik
BASEMAP_ZOOM = 18
BOUNDARY_STYLE = {'edgecolor': '#FF0000', 'facecolor': 'none', 'linewidth': 1.5, 'zorder': 4}
MASK_STYLE = {'facecolor': 'black', 'edgecolor': 'none', 'alpha': 0.4, 'zorder': 3}

# --- ReportLab Paragraph Style Attributes Dictionaries ---
BASE_NORMAL_STYLE_ATTRS = {'fontSize': 7, 'leading': 9, 'fontName': 'Helvetica'}
TITLE_RL_STYLE_ATTRS = {'alignment': TA_CENTER, 'fontSize': 16, 'spaceAfter': 0.15*inch,
                          'fontName': 'Helvetica-Bold', 'keepWithNext': 1}
STREET_HEADER_RL_STYLE_ATTRS = {'fontName': 'Helvetica-Bold', 'backColor': colors.Color(0.9,0.9,0.9),
                                 'alignment': TA_LEFT, 'leftIndent': 0}

KML_ADDRESS_COMPONENT_TAGS = {
    'house_number': ["STREET_NUM", "AD_ADDRESS", "AM_ADDRE_1"],
    'street_prefix': ["STREET_PRE", "AM_DIR_PRE"],
    'street_name': ["STREET_NAM", "AM_STR_NAM"],
    'street_type': ["STREET_TYP", "AM_STR_TYP"],
    'street_suffix': ["STREET_SUF", "AM_DIR_SUF"],
    'unit_type': ["UNIT_TYPE"],
    'unit_number': ["UNIT_NUMBE"],
    'city': ["CITY", "AM_TOWN"],
    'state': ["STATE", "AM_STATE"],
    'zip': ["ZIP", "AM_ZIP"]
}
TARGET_CRS = "EPSG:3857"
# LOADED_KML_GDF_CACHE # This was for the worker, remove global if not used globally anymore

# --- Helper function for natural sorting ---
def natural_sort_key(s):
    if s is None: return ()
    if not isinstance(s, str): return (s,)
    parts = re.split('([0-9]+)', s); key_parts = []
    for text in parts:
        if text.isdigit(): key_parts.append(int(text))
        elif text: key_parts.append(text.lower())
    return tuple(key_parts)

# --- KML Loading Function (for worker thread) ---
def load_and_prepare_kml_data_for_worker(kml_file_path, component_tags_map, log_emitter):
    log_emitter(f"  Loading KML file with pykml: {kml_file_path}...")
    extracted_data_list = []
    try:
        with open(kml_file_path, 'rb') as f: doc = parser.parse(f).getroot()
        namespaces = {'kml': 'http://www.opengis.net/kml/2.2', 'gx': 'http://www.google.com/kml/ext/2.2'}
        all_placemarks = doc.findall('.//kml:Placemark', namespaces=namespaces)
        log_emitter(f"    - Found {len(all_placemarks)} total placemarks.")
        for placemark in all_placemarks:
            point_element = placemark.find('.//kml:Point/kml:coordinates', namespaces=namespaces)
            if point_element is not None and point_element.text:
                try:
                    coords_text = point_element.text.strip();lon_str,lat_str=coords_text.split(',')[:2];lon,lat=float(lon_str),float(lat_str)
                except ValueError: continue
                placemark_data = {'geometry': Point(lon, lat)}; has_primary_house_num = False
                for component_key, tag_names_list in component_tags_map.items():
                    component_value = None
                    for tag_name in tag_names_list:
                        value_found = None; extended_data_element = placemark.find('.//kml:ExtendedData', namespaces=namespaces)
                        if extended_data_element is not None:
                            simple_data_element = extended_data_element.find(f".//kml:SimpleData[@name='{tag_name}']", namespaces=namespaces)
                            if simple_data_element is not None: value_found = simple_data_element.text
                        if value_found is not None and str(value_found).strip(): component_value = str(value_found).strip(); break
                    placemark_data[component_key] = component_value
                    if component_key == 'house_number' and component_value: has_primary_house_num = True
                if (not has_primary_house_num) and "__name__" in component_tags_map.get('house_number', []):
                    name_el = placemark.find('./kml:name', namespaces=namespaces)
                    if name_el is not None and name_el.text and str(name_el.text).strip().isdigit():
                        placemark_data['house_number'] = str(name_el.text).strip(); has_primary_house_num = True
                if has_primary_house_num: extracted_data_list.append(placemark_data)
        
        log_emitter(f"    - Extracted {len(extracted_data_list)} address entries with house numbers.")
        if not extracted_data_list:
            log_emitter("    - No address entries could be extracted."); return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        gdf_kml_addresses = gpd.GeoDataFrame(extracted_data_list, crs="EPSG:4326")
        return gdf_kml_addresses
    except FileNotFoundError: log_emitter(f"  ERROR: KML file not found: {kml_file_path}"); return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    except etree.XMLSyntaxError as xml_err: log_emitter(f"  ERROR: KML XML Syntax: {xml_err}"); return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    except Exception as e: log_emitter(f"  ERROR KML parsing: {e}\n{traceback.format_exc()}"); return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

# --- Worker Thread for Processing ---
class ProcessingWorker(QThread):
    progress_updated = pyqtSignal(int, int, str)
    log_message = pyqtSignal(str)
    processing_finished = pyqtSignal(str)
    kml_data_loaded = pyqtSignal(bool, str)

    def __init__(self, csv_path, kml_path, output_folder):
        super().__init__()
        self.csv_path = csv_path
        self.kml_path = kml_path
        self.output_folder = output_folder
        self.is_cancelled = False
        self.loaded_kml_gdf_original_crs = None

    def _emit_log(self, message):
        self.log_message.emit(message)

    def run(self):
        try:
            self._emit_log("--- Processing Started ---")
            self.loaded_kml_gdf_original_crs = load_and_prepare_kml_data_for_worker(
                self.kml_path, KML_ADDRESS_COMPONENT_TAGS, self._emit_log
            )
            if self.is_cancelled: self.processing_finished.emit("Processing cancelled."); return
            if self.loaded_kml_gdf_original_crs is None or self.loaded_kml_gdf_original_crs.empty:
                self.kml_data_loaded.emit(False, "KML data empty or failed to load. House numbers will be missing.")
                self.loaded_kml_gdf_original_crs = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            else:
                self.kml_data_loaded.emit(True, f"KML loaded: {len(self.loaded_kml_gdf_original_crs)} addresses found.")

            projected_kml_gdf_wm = None
            if not self.loaded_kml_gdf_original_crs.empty:
                self._emit_log(f"  Projecting all KML addresses to {TARGET_CRS} (one-time)...")
                try:
                    projected_kml_gdf_wm = self.loaded_kml_gdf_original_crs.to_crs(TARGET_CRS)
                except Exception as proj_err:
                    self._emit_log(f"  ERROR projecting KML data: {proj_err}")
                    projected_kml_gdf_wm = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)
            else:
                projected_kml_gdf_wm = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)

            self._emit_log(f"Loading CSV: {self.csv_path}")
            df = pd.read_csv(self.csv_path, keep_default_na=True, na_values=['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA', 'NULL', 'NaN', 'n/a', 'nan', 'null'])
            total_rows = len(df)
            self._emit_log(f"Loaded {total_rows} rows from CSV.")
            max_required_index = max(TERRITORY_NAME_INDEX,TERRITORY_NUMBER_INDEX,BOUNDARY_COLUMN_INDEX)
            if df.shape[1] <= max_required_index:
                self.processing_finished.emit("Error: CSV columns mismatch."); return

            temp_map_image_filename = os.path.join(self.output_folder, "_temp_map_image.png")

            for index, row_data in df.iterrows():
                if self.is_cancelled: break
                self.progress_updated.emit(index, total_rows, f"Territory {index + 1}/{total_rows}")
                
                territory_name, territory_number = f"Row_{index}_Err", "Num_Err"
                gdf_territory_wm = None; gdf_filtered_kml_addresses_wm = None
                try:
                    territory_name_raw = row_data.iloc[TERRITORY_NAME_INDEX]; territory_number_raw = row_data.iloc[TERRITORY_NUMBER_INDEX]; boundary_obj = row_data.iloc[BOUNDARY_COLUMN_INDEX]
                    if pd.isna(territory_name_raw) or pd.isna(boundary_obj): self._emit_log(f" Skip {index}"); continue
                    territory_name = str(territory_name_raw).strip(); boundary_str = str(boundary_obj).strip();
                    if not boundary_str: self._emit_log(f" Skip {index} empty boundary"); continue
                    if pd.isna(territory_number_raw): territory_number = "NoNum"
                    else:
                        try: territory_number = str(int(float(territory_number_raw)))
                        except: territory_number = str(territory_number_raw).strip()
                    self._emit_log(f"\nProcessing: {territory_name} - {territory_number} (Row {index})")

                    try:
                         boundary_coords = ast.literal_eval(boundary_str); polygon = Polygon(boundary_coords)
                         if not polygon.is_valid: polygon = polygon.buffer(0)
                         if not polygon.is_valid: raise ValueError("Invalid geometry.")
                         gdf_territory = gpd.GeoDataFrame({"T":[territory_name]}, geometry=[polygon], crs="EPSG:4326")
                         gdf_territory_wm = gdf_territory.to_crs(TARGET_CRS)
                         if gdf_territory_wm.geometry.iloc[0] is None or not gdf_territory_wm.geometry.iloc[0].is_valid: raise ValueError("Territory invalid after projection.")
                    except Exception as geom_err: self._emit_log(f"  Geom Error {territory_name}: {geom_err}"); continue
                    
                    self._emit_log("  Filtering KML addresses...")
                    if not projected_kml_gdf_wm.empty:
                        try:
                            current_territory_polygon_wm = gdf_territory_wm.geometry.iloc[0]
                            if not current_territory_polygon_wm.is_valid: current_territory_polygon_wm = current_territory_polygon_wm.buffer(0)
                            is_within = projected_kml_gdf_wm.geometry.within(current_territory_polygon_wm)
                            gdf_filtered_kml_addresses_wm = projected_kml_gdf_wm[is_within].copy()
                            self._emit_log(f"    - Found {len(gdf_filtered_kml_addresses_wm)} KML addresses in territory.")
                        except Exception as filter_err: self._emit_log(f"    - Error filtering: {filter_err}"); gdf_filtered_kml_addresses_wm = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)
                    else: self._emit_log("    - No KML data to filter."); gdf_filtered_kml_addresses_wm = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)

                    self._emit_log("  Generating map image...")
                    fig_map, ax_map = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_MAP_HEIGHT_INCHES), dpi=MAP_IMAGE_DPI)
                    ax_map.set_axis_off(); gdf_territory_wm.plot(ax=ax_map, edgecolor='none', facecolor='none', alpha=0)
                    basemap_added = False
                    try:
                        with warnings.catch_warnings(): warnings.simplefilter("ignore", UserWarning); ctx.add_basemap(ax_map, crs=gdf_territory_wm.crs, source=BASEMAP_PROVIDER, zoom=BASEMAP_ZOOM, attribution_size=6, interpolation='spline36')
                        basemap_added = True
                    except Exception as ctx_err: self._emit_log(f"  Ctx Error for {territory_name}: {ctx_err}.")
                    if basemap_added:
                        try:
                            final_xlim,final_ylim=ax_map.get_xlim(),ax_map.get_ylim(); map_bounds=box(final_xlim[0],final_ylim[0],final_xlim[1],final_ylim[1])
                            terr_geom=gdf_territory_wm.geometry.iloc[0];
                            if not terr_geom.is_valid: terr_geom=terr_geom.buffer(0)
                            if terr_geom.is_valid: gpd.GeoDataFrame([1],geometry=[map_bounds.difference(terr_geom)],crs=gdf_territory_wm.crs).plot(ax=ax_map,**MASK_STYLE)
                        except Exception as mask_err: self._emit_log(f"  Mask Error for {territory_name}: {mask_err}")
                    gdf_territory_wm.plot(ax=ax_map, **BOUNDARY_STYLE)
                    plt.savefig(temp_map_image_filename, dpi=MAP_IMAGE_DPI, bbox_inches='tight', pad_inches=0.02)
                    plt.close(fig_map); self._emit_log(f"  Map image saved: {temp_map_image_filename}")

                    self._emit_log("  Generating ReportLab PDF...")
                    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in territory_name).rstrip() or f"Territory_Row_{index}"
                    safe_number = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in territory_number).rstrip() or "NoNum"
                    pdf_filename = f"{safe_name}-{safe_number}.pdf"; pdf_output_file = os.path.join(self.output_folder, pdf_filename)
                    doc = SimpleDocTemplate(pdf_output_file, pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
                    story = []; base_styles = getSampleStyleSheet()

                    # --- Corrected Style Instantiation ---
                    title_rl_style = ParagraphStyle('TerritoryTitleInst', parent=base_styles['h1'], **TITLE_RL_STYLE_ATTRS)
                    normal_style_rl = ParagraphStyle('NormalSmallInst', parent=base_styles['Normal'], **BASE_NORMAL_STYLE_ATTRS)
                    street_header_rl_style = ParagraphStyle('StreetHeaderInst', parent=normal_style_rl, **STREET_HEADER_RL_STYLE_ATTRS)
                    # --- End Corrected Style Instantiation ---

                    story.append(Paragraph(f"{territory_name} - {territory_number}", title_rl_style))
                    if os.path.exists(temp_map_image_filename):
                        try:
                            with PILImage.open(temp_map_image_filename) as img_pil: actual_img_width_px, actual_img_height_px = img_pil.size
                            img_aspect_ratio = actual_img_height_px / actual_img_width_px if actual_img_width_px > 0 else 1
                            img_draw_width = doc.width; img_draw_height = img_draw_width * img_aspect_ratio
                            max_img_height_on_page = doc.height - (title_rl_style.fontSize + title_rl_style.spaceAfter + 0.2*inch)
                            if img_draw_height > max_img_height_on_page:
                                img_draw_height = max_img_height_on_page
                                img_draw_width = img_draw_height / img_aspect_ratio if img_aspect_ratio > 0 else doc.width
                            map_img_rl = Image(temp_map_image_filename, width=img_draw_width, height=img_draw_height)
                            story.append(map_img_rl); story.append(Spacer(1, 0.2*inch))
                        except Exception as img_err: self._emit_log(f" Error PDF image for {territory_name}: {img_err}"); story.append(Paragraph("Map image error.", normal_style_rl))
                    else: story.append(Paragraph("Map image file not found.", normal_style_rl))

                    if gdf_filtered_kml_addresses_wm is not None and not gdf_filtered_kml_addresses_wm.empty:
                        gdf_filtered_kml_addresses_wm['full_street_display'] = gdf_filtered_kml_addresses_wm.apply(lambda r: " ".join(filter(None, [r.get('street_prefix'), r.get('street_name'), r.get('street_type'), r.get('street_suffix')])).upper().strip(), axis=1)
                        gdf_filtered_kml_addresses_wm['address_display'] = gdf_filtered_kml_addresses_wm.apply(lambda r: " ".join(filter(None, [r.get('house_number'), r.get('street_prefix'), r.get('street_name'), r.get('street_type'), r.get('street_suffix')])).strip(), axis=1)
                        gdf_filtered_kml_addresses_wm['unit_display'] = gdf_filtered_kml_addresses_wm.apply(lambda r: " ".join(filter(None, [r.get('unit_type'), r.get('unit_number')])).strip(), axis=1)
                        gdf_filtered_kml_addresses_wm['locality_display'] = gdf_filtered_kml_addresses_wm.apply(lambda r: ", ".join(filter(None, [r.get('city'), f"{r.get('state', '')} {r.get('zip', '')}".strip()])).strip(), axis=1)
                        gdf_filtered_kml_addresses_wm['sort_key_house_num'] = gdf_filtered_kml_addresses_wm['house_number'].apply(natural_sort_key)
                        gdf_sorted_addresses = gdf_filtered_kml_addresses_wm.sort_values(by=['full_street_display', 'sort_key_house_num'])
                        
                        data_for_table = [[Paragraph("<b>Address</b>", normal_style_rl), Paragraph("<b>Unit</b>", normal_style_rl), Paragraph("<b>City, State Zip</b>", normal_style_rl)]]
                        current_street_header_text = None
                        for _, addr_row in gdf_sorted_addresses.iterrows():
                            if current_street_header_text != addr_row['full_street_display']:
                                current_street_header_text = addr_row['full_street_display']
                                data_for_table.append([Paragraph(f"{current_street_header_text}", street_header_rl_style), "", ""])
                            
                            p_address = Paragraph(addr_row['address_display'] or '-', normal_style_rl); p_unit = Paragraph(addr_row['unit_display'] or '-', normal_style_rl); p_locality = Paragraph(addr_row['locality_display'] or '-', normal_style_rl)
                            data_for_table.append([p_address, p_unit, p_locality])

                        if len(data_for_table) > 1:
                            table_col_widths = [doc.width*0.45, doc.width*0.15, doc.width*0.35]
                            address_rl_table = Table(data_for_table, colWidths=table_col_widths, repeatRows=1, splitByRow=1)
                            ts = TableStyle([
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#40466e')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8),
                                ('BOTTOMPADDING', (0,0), (-1,0), 6), ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
                                ('BOTTOMPADDING', (0,1), (-1,-1), 4), ('TOPPADDING', (0,1), (-1,-1), 4),
                                ('GRID', (0,0), (-1,-1), 0.25, colors.darkgrey), ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
                            ])
                            row_idx_for_style = 0
                            for i, r_data in enumerate(data_for_table):
                                if i == 0: continue # Skip actual table header
                                # Check if it's one of our Paragraph-based street headers
                                if isinstance(r_data[0], Paragraph) and r_data[0].style == street_header_rl_style:
                                    ts.add('SPAN', (0, i), (2, i)); ts.add('BACKGROUND', (0, i), (2, i), colors.Color(0.92,0.92,0.92));
                                    ts.add('TEXTCOLOR', (0,i), (0,i), colors.black); ts.add('BOTTOMPADDING', (0,i), (2,i), 3); ts.add('TOPPADDING', (0,i), (2,i), 5)
                                    ts.add('LINEBELOW', (0, i), (2, i), 0.5, colors.grey); row_idx_for_style = 0 # Reset for zebra
                                elif row_idx_for_style % 2 == 0 : ts.add('BACKGROUND', (0,i), (-1,i), colors.white) # White rows
                                else: ts.add('BACKGROUND', (0,i), (-1,i), colors.Color(0.96,0.96,0.96)) # Light grey rows
                                # Increment only for actual data rows, not our custom street headers
                                if not (isinstance(r_data[0], Paragraph) and r_data[0].style == street_header_rl_style):
                                    row_idx_for_style +=1
                            address_rl_table.setStyle(ts); story.append(address_rl_table)
                        else: story.append(Paragraph("No addresses in territory.", normal_style_rl))
                    else: story.append(Paragraph("No KML data for table for this territory.", normal_style_rl))

                    doc.build(story); self._emit_log(f"  Saved ReportLab PDF: {pdf_output_file}")
                    if os.path.exists(temp_map_image_filename): os.remove(temp_map_image_filename)

                except Exception as row_err:
                    self._emit_log(f"  --- Error row {index} ({territory_name} - {territory_number}) ---")
                    self._emit_log(f"  Details: {row_err}\n{traceback.format_exc()}")
                finally:
                    if 'fig_map' in locals() and plt.fignum_exists(fig_map.number): plt.close(fig_map)
                    if 'gdf_territory_wm' in locals(): del gdf_territory_wm
                    if 'gdf_filtered_kml_addresses_wm' in locals(): del gdf_filtered_kml_addresses_wm
            
            if self.is_cancelled: self.processing_finished.emit("Processing cancelled by user.")
            else: self.progress_updated.emit(total_rows, total_rows, "All territories processed."); self.processing_finished.emit("Processing complete!")
        except Exception as e:
            self._emit_log(f"--- Critical Error in Worker Thread ---\nError: {e}\n{traceback.format_exc()}")
            self.processing_finished.emit(f"Error: {e}")

    def stop(self): self.is_cancelled = True; self._emit_log("Cancellation requested...")

# --- PyQt6 Main Application Window ---
class MapGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Territory Map & Address PDF Generator")
        self.setGeometry(100, 100, 700, 600) # x, y, width, height

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_file_selection_ui("CSV File:", "_csv_path_edit", "_select_csv_button", self._select_csv_file)
        self._create_file_selection_ui("KML File:", "_kml_path_edit", "_select_kml_button", self._select_kml_file)
        self._create_file_selection_ui("Output Folder:", "_output_folder_edit", "_select_output_button", self._select_output_folder, is_folder=True)

        self.generate_button = QPushButton("Generate PDFs")
        self.generate_button.clicked.connect(self._start_processing)
        self.main_layout.addWidget(self.generate_button)

        self.cancel_button = QPushButton("Cancel Processing")
        self.cancel_button.clicked.connect(self._cancel_processing)
        self.cancel_button.setEnabled(False)
        self.main_layout.addWidget(self.cancel_button)

        self.status_label = QLabel("Status: Idle")
        self.main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.main_layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.main_layout.addWidget(self.log_area)

        self.worker_thread = None
        self.processing_worker = None

        default_output_folder_name = "Generated_Map_PDFs"
        default_output = os.path.join(os.getcwd(), default_output_folder_name)
        self._output_folder_edit.setText(default_output)

    def _create_file_selection_ui(self, label_text, edit_attr_name, button_attr_name, slot_method, is_folder=False):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        layout.addWidget(label)
        
        line_edit = QLineEdit()
        setattr(self, edit_attr_name, line_edit)
        layout.addWidget(line_edit)
        
        button = QPushButton("Browse...")
        button.clicked.connect(slot_method)
        setattr(self, button_attr_name, button)
        layout.addWidget(button)
        
        self.main_layout.addLayout(layout)

    def _select_csv_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if path:
            self._csv_path_edit.setText(path)

    def _select_kml_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select KML File", "", "KML Files (*.kml)")
        if path:
            self._kml_path_edit.setText(path)

    def _select_output_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self._output_folder_edit.setText(path)

    def _start_processing(self):
        csv_path = self._csv_path_edit.text()
        kml_path = self._kml_path_edit.text()
        output_folder = self._output_folder_edit.text()

        if not (csv_path and os.path.exists(csv_path)):
            QMessageBox.warning(self, "Input Error", "Please select a valid CSV file.")
            return
        if not (kml_path and os.path.exists(kml_path)):
            QMessageBox.warning(self, "Input Error", "Please select a valid KML file.")
            return
        if not output_folder:
            QMessageBox.warning(self, "Input Error", "Please select a valid output folder.")
            return
        
        os.makedirs(output_folder, exist_ok=True)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.log_message_slot("Starting processing...")

        self.processing_worker = ProcessingWorker(csv_path, kml_path, output_folder)
        self.worker_thread = QThread()
        self.processing_worker.moveToThread(self.worker_thread)

        self.processing_worker.progress_updated.connect(self.update_progress_slot)
        self.processing_worker.log_message.connect(self.log_message_slot)
        self.processing_worker.processing_finished.connect(self.processing_finished_slot)
        self.processing_worker.kml_data_loaded.connect(self.kml_loaded_slot)

        self.worker_thread.started.connect(self.processing_worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.processing_worker.finished.connect(self.worker_thread.quit)
        self.processing_worker.finished.connect(self.processing_worker.deleteLater)

        self.worker_thread.start()

    def _cancel_processing(self):
        if self.processing_worker:
            self.processing_worker.stop()
        self.cancel_button.setEnabled(False)

    def kml_loaded_slot(self, success, message):
        self.log_message_slot(f"KML Load Status: {message}")
        if not success:
            QMessageBox.warning(self, "KML Loading Error", message)

    def update_progress_slot(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Status: {message}")

    def log_message_slot(self, message):
        self.log_area.append(message)

    def processing_finished_slot(self, message):
        self.status_label.setText(f"Status: {message}")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if "Error" in message and not "Processing cancelled" in message : # Don't show error box if user cancelled
            QMessageBox.critical(self, "Processing Error", message)
        elif not "Processing cancelled" in message:
            QMessageBox.information(self, "Processing Complete", message)
        
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.processing_worker = None

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log_message_slot("Application closing, attempting to stop worker thread...")
            self.processing_worker.stop()
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):
                self.log_message_slot("Worker thread did not stop gracefully.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapGeneratorApp()
    window.show()
    sys.exit(app.exec())