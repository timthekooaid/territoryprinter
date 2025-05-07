# 🗺️ Territory Map & Address List Generator ✨

<img src="https://github.com/user-attachments/assets/813e0663-da60-4ddc-8d2e-befc5919b539" width="300" />


Generate beautiful, high-resolution PDF territory maps complete with detailed address lists, ready for print or digital use. Combines clear OpenStreetMap backgrounds with precise KML address data overlays.

---
<img src="https://github.com/user-attachments/assets/7bb84771-be87-471e-88fa-99898a52ec73" width="600" />


---

## ⚙️ Installation & Setup

1.  **Install Dependencies:**
    ```bash
    pip install pandas geopandas matplotlib shapely contextily pykml lxml reportlab Pillow PyQt6
    ```

## ▶️ How to Use

## 📍 Preparing the Address KML (using QGIS)

This application requires a single KML file containing all necessary address points. If you have separate address point data for different areas (e.g., Loudoun County, Fairfax County), you can merge them using QGIS:

1.  **Open QGIS:** Launch the QGIS Desktop application.
2.  **Add Address Layers:** Add your vector point layers for Loudoun and Fairfax addresses (e.g., Shapefiles, GeoPackages). Ensure these layers contain the necessary attribute columns (like `STREET_NUM`, `STREET_NAM`, `CITY`, `ZIP`, etc.).
3.  **Merge Layers:**
    *   Go to the main menu: `Vector` -> `Data Management Tools` -> `Merge Vector Layers`.
    *   In the dialog box:
        *   Click the `...` button next to "Input layers" and select both your Loudoun and Fairfax address layers. Click OK.
    *   Click "Run". A new merged layer will be added to your QGIS project.
4.  **Export Merged Layer as KML:**
    *   In the QGIS Layers Panel, right-click on the **newly created merged layer**.
    *   Select `Export` -> `Save Features As...`.
    *   In the "Save Vector Layer as..." dialog:
        *   Set **Format:** to `Keyhole Markup Language [KML]`.
        *   Click the `...` button next to **File name** and choose a location and name for your final KML file (e.g., `all_addresses.kml`).
        *   Ensure **CRS:** is `EPSG:4326 - WGS 84`.
        *   Under "Select fields to export and their export options", make sure all the necessary address component fields (`STREET_NUM`, `STREET_NAM`, `UNIT_NUMBE`, `CITY`, `ZIP`, etc.) are checked for export.
    *   Click **OK**.
5.  **Use KML:** The generated `all_addresses.kml` (or your chosen name) is the file you should select when prompted by the Python application.

1.  **Run the Application:**
    ```bash
    MapGenerator.exe
    ```
2.  **Select Files:**
    *   Use the "Browse..." buttons to select your territory **CSV file**.
    *   Select your **KML file** containing the address points.
    *   Choose an **Output Folder** where the PDFs will be saved.
3.  **Generate:** Click the "Generate PDFs" button.
4.  **Monitor Progress:** Watch the status bar, progress bar, and log area for updates.
5.  **Done!** PDFs will appear in your selected output folder upon completion.
