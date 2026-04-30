#!/usr/bin/env python3
"""
create_code_interpreter.py

Creates a Vertex AI Code Interpreter Extension and prints the resource name
to add to your .env file as CODE_INTERPRETER_EXTENSION_NAME.

Usage:
    python3 create_code_interpreter.py
"""

import sys

try:
    import vertexai
    from vertexai.preview.extensions import Extension
except ImportError:
    print("ERROR: vertexai package not found. Run: pip install google-adk")
    sys.exit(1)


def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Vertex AI Code Interpreter Extension Setup")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    project_id = input("Enter your GCP Project ID: ").strip()
    if not project_id:
        print("ERROR: Project ID cannot be empty.")
        sys.exit(1)

    print()
    print("Note: Code Interpreter Extensions must be created in the")
    print("global location to work with preview Gemini models.")
    region = input("Enter region [global]: ").strip() or "global"

    print()
    print(f"Creating Code Interpreter Extension...")
    print(f"  Project  : {project_id}")
    print(f"  Location : {region}")
    print()

    try:
        vertexai.init(project=project_id, location=region)
        ext = Extension.from_hub("code_interpreter")
        resource_name = ext.gca_resource.name

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  Extension created successfully.")
        print()
        print("  Add the following to your .env file:")
        print()
        print(f"  CODE_INTERPRETER_EXTENSION_NAME={resource_name}")
        print()
        print("  This extension can be reused across deployments.")
        print("  Do not create a new one on each deploy.")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        print(f"ERROR: Failed to create extension: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
