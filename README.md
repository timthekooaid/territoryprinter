# 🗺️ Territory Map & Address List Generator ✨

<img src="https://github.com/user-attachments/assets/813e0663-da60-4ddc-8d2e-befc5919b539" width="300" />


Generate beautiful, high-resolution PDF territory maps complete with detailed address lists, ready for print or digital use. Combines clear OpenStreetMap backgrounds with precise KML address data overlays.

---
<img src="https://github.com/user-attachments/assets/7bb84771-be87-471e-88fa-99898a52ec73" width="300" />


---

## 🚀 Key Features

*   **Modern GUI:** Easy-to-use graphical interface built with PyQt6 for Windows.
*   **CSV Input:** Define territory boundaries and identifiers using a simple CSV file.
*   **KML Integration:** Overlay accurate address points (including house numbers) directly from your local KML files.
*   **High-Quality Maps:** Utilizes clear OpenStreetMap background tiles (`contextily`) zoomed appropriately for detail.
*   **Territory Focus:** Automatically dims the map area outside the specified territory boundary for better visibility.
*   **Detailed Address Lists:** Generates multi-page, spreadsheet-style address tables within the PDF, grouped by street and naturally sorted (`reportlab`).
*   **Responsive UI:** Map generation runs in the background, keeping the application responsive (`QThread`).
*   **PDF Output:** Creates professional, high-resolution PDF files perfect for printing or sharing.

## 🛠️ Technologies Used

*   **Python 3**
*   **PyQt6:** For the graphical user interface.
*   **ReportLab:** For advanced PDF generation and table creation.
*   **GeoPandas & Shapely:** For spatial data handling and operations.
*   **Contextily:** For fetching and displaying OpenStreetMap background map tiles.
*   **pyKML & lxml:** For robust KML file parsing.
*   **Pandas:** For efficient CSV data reading.
*   **Pillow (PIL):** For image handling.

## ⚙️ Installation & Setup

1.  **Clone or Download:** Get the code from this repository.
2.  **Python:** Ensure you have Python 3.9+ installed and added to your PATH.
3.  **Create Virtual Environment (Recommended):**
    ```bash
    cd your-project-folder
    python -m venv venv
    venv\Scripts\activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install pandas geopandas matplotlib shapely contextily pykml lxml reportlab Pillow PyQt6
    ```
    *(Note: Installing GeoPandas on Windows might require extra steps if `pip` fails. Using `conda` or pre-compiled wheels might be necessary. See GeoPandas documentation.)*

## ▶️ How to Use

1.  **Activate Virtual Environment** (if you created one):
    ```bash
    venv\Scripts\activate
    ```
2.  **Run the Application:**
    ```bash
    python map_generator_gui.py
    ```
3.  **Select Files:**
    *   Use the "Browse..." buttons to select your territory **CSV file**.
    *   Select your **KML file** containing the address points.
    *   Choose an **Output Folder** where the PDFs will be saved.
4.  **Generate:** Click the "Generate PDFs" button.
5.  **Monitor Progress:** Watch the status bar, progress bar, and log area for updates.
6.  **Done!** PDFs will appear in your selected output folder upon completion.

*(Optional: To create a standalone `.exe`, use PyInstaller after installation: `pyinstaller --onefile --windowed --name TerritoryMapper your_script_name.py`. You may need to add `--hidden-import` flags if PyInstaller misses dependencies like `rasterio.sample`)*

---

Enjoy generating your maps! 💡
