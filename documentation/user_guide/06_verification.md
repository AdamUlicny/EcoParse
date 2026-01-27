# Verification

Once the extraction process is complete, verification is a crucial step to ensure the accuracy of your data.




## Workflow

### 1. Initial Quick Check
Before diving deep into individual records, perform a quick visual inspection of the results. 
- Check if the extracted data broadly resembles what you expect from the original document.
- Ensure that the fields you configured are being populated.

### 2. Deep Dive with the Verification Tab
Switch to the **Verification** tab to inspect the extraction details for specific species.

**What you will see:**
- **View Options**: Toggle between **Text Context** and **Document Images** using the radio buttons at the top of the context panel.
- **Text Context**: Displays the extracted text chunks with relevant terms highlighted (as described previously).
- **Document Images**: Generates and displays the actual PDF page images where the species was found. This is useful for verifying layout-dependent information or checking figures/tables.

> **Note on Images**: Image generation happens on-the-fly. If you have many mentions, it might take a moment to render the pages.

> **About Highlighting:** In Text Context view, the highlighting feature helps quickly spot data points.

## Saving Your Results

Once you are satisfied with the verification process, you can save your work.

### Output Formats
- **CSV or JSON**: You can export the raw extraction results in standard CSV or JSON formats for further analysis.

### Recommended: Save Extraction Report (JSON)
We highly recommend saving the **JSON report** of the extraction.
- **Why?** In addition to the results, this file preserves your extraction **settings** and **few-shot examples**.
- **Benefit:** This ensures **reproducibility**, allowing you or others to replicate the extraction process with the exact same configuration later.
