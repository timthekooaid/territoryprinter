# 🗺️ Territory Map & Address List Generator ✨

<img src="https://github.com/user-attachments/assets/813e0663-da60-4ddc-8d2e-befc5919b539" width="300" />


Generate beautiful, high-resolution PDF territory maps complete with detailed address lists, ready for print or digital use. Combines clear OpenStreetMap backgrounds with precise KML address data overlays.

---
<img src="https://github.com/user-attachments/assets/7bb84771-be87-471e-88fa-99898a52ec73" width="600" />


---
### prereqs
*   **Python 3**
*   **PyQt6:** For the graphical user interface.
*   **ReportLab:** For advanced PDF generation and table creation.
*   **GeoPandas & Shapely:** For spatial data handling and operations.
*   **Contextily:** For fetching and displaying OpenStreetMap background map tiles.
*   **pyKML & lxml:** For robust KML file parsing.
*   **Pandas:** For efficient CSV data reading.
*   **Pillow (PIL):** For image handling.

## ⚙️ Installation & Setup

1.  **Install Dependencies:**
    ```bash
    pip install pandas geopandas matplotlib shapely contextily pykml lxml reportlab Pillow PyQt6
    ```

## ▶️ How to Use

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
