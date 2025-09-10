import sys
from tools.google_exporter import create_lesson_doc  # adjust if your module has a different name

def validate_content(content: list[dict]) -> bool:
    if not isinstance(content, list):
        print("❌ Content is not a list.")
        return False
    for idx, el in enumerate(content):
        if not isinstance(el, dict):
            print(f"❌ Element at index {idx} is not a dict.")
            return False
        if "text" not in el:
            print(f"❌ Element at index {idx} is missing 'text' field.")
            return False
    return True

def main():
    # Sample test input
    test_content = [
        { "text": "Subject-Verb Agreement", "style": "HEADING_1" },
        { "text": "Subject-verb agreement means that the subject and verb must match in number.", "style": "NORMAL_TEXT" },
        { "text": "Key Points", "style": "HEADING_2" },
        { "text": "Singular subjects take singular verbs.", "bold": True },
        { "text": "Plural subjects take plural verbs." }
    ]
    title = "Subject-Verb Agreement Lesson"

    # Validate content first
    if not validate_content(test_content):
        print("❌ Validation failed. Exiting.")
        sys.exit(1)

    # Try creating the document
    try:
        url = create_lesson_doc(test_content, title)
        print(f"✅ Success! Document created: {url}")
    except Exception as e:
        print("❌ An error occurred during export:")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()

