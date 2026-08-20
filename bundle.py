import os

def bundle_codebase(output_file="codebase.md"):
    # Clear or create the file
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("# MY AGENTIC CHATBOT CODEBASE\n\n")
        
        # Track if we actually find any files
        file_count = 0
        
        for root, dirs, files in os.walk("."):
            # Exclude folders safely by mutating 'dirs' in place
            # This skips hidden git folders and virtual environments
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '.venv', 'env', '__pycache__']]
                
            for file in files:
                # Capture python files, but ignore this bundler script and the output file
                if file.endswith(".py") and file != "bundle.py" and file != output_file:
                    file_path = os.path.join(root, file)
                    outfile.write(f"## File: {file_path}\n")
                    outfile.write("```python\n")
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                        file_count += 1
                    except Exception as e:
                        outfile.write(f"# Error reading file: {str(e)}\n")
                    outfile.write("\n```\n\n")
                    
    print(f"Success! Bundled {file_count} Python files into {output_file}")

if __name__ == "__main__":
    bundle_codebase()