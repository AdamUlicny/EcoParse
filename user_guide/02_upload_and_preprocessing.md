# 2. Upload and Preprocessing (Tab 1)

This step prepares your document for extraction by converting the PDF into raw text.

## 2.1 File Upload
Start by uploading your target `.pdf` file in **Tab 1**.

![Screenshot of the file upload interface](placeholder_upload_interface)

## 2.2 Select Page Range
After uploading, it is highly recommended to select a specific page range for processing.

*   **Why?** Removing introductions, indices, and reference sections significantly reduces "false positives" (detecting species names that are not the focus of the redlist assessment).
*   **How?** Quickly look through the PDF in a separate window and type in the pages where the redlist assessments start and end. EcoParse will then automatically remove any pages outside of this range. 

## 2.3 Extract Text
EcoParse offers multiple text extraction approaches to handle various file encodings and languages.

1.  Select an extraction method.
2.  Run te extraction.
3.  **Verify Output**: Check the preview window to ensure the formatting looks correct (e.g., spaces are preserved, special characters are readable).

> **Note:** Some languages or older PDFs may require trying different extraction methods to get the best result.

![Example of extracted text preview](placeholder_text_extraction_preview)
