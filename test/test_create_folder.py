# test_google_exporter.py

from tools.google_exporter import create_lesson_doc, create_mcq_sheet

def main():
    print("🚀 Starting test export...")

    # Create a simple doc
    doc_url = create_lesson_doc(
        content=[
            {"text": "Test Document Title", "style": "HEADING_1"},
            {"text": "This is a sample paragraph.", "bold": True}
        ],
        title="Test Document"
    )
    print(f"✅ Created Google Doc: {doc_url}")

    # Create a simple sheet
    sheet_url = create_mcq_sheet(
        rows=[
            ["Question", "Option A", "Option B", "Option C", "Option D", "Answer", "Rationale"],
            ["What is 2 + 2?", "3", "4", "5", "6", "B", "Because 2 + 2 = 4."]
        ],
        title="Test MCQ Sheet"
    )
    print(f"✅ Created Google Sheet: {sheet_url}")

    print("🏁 Test complete!")

if __name__ == "__main__":
    main()

