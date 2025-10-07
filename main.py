from datetime import datetime
import os
from resume.generator import ResumeGenerator
from coverletter.generator import CoverLetterGenerator

def get_user_choice():
    while True:
        print("\nWhat would you like to generate?")
        print("1. Resume only")
        print("2. Cover Letter only")
        print("3. Both Resume and Cover Letter")
        choice = input("Enter your choice (1-3): ")

        if choice in ['1', '2', '3']:
            return choice

def get_job_description_url():
    return input("\nEnter job description URL (press Enter to skip): ").strip()

def get_company_name():
    return input("\nEnter company name: ").strip()

def get_role_name():
    """Get role name from user"""
    return input("\nEnter role name (e.g. Software Engineer Intern): ").strip()

def create_output_structure(base_dir, company_name, role_name):
    """Create simplified output directory structure: applications/COMPANY/"""
    
    # Clean company name for directory
    company_dir = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Create simple structure: applications/COMPANY/
    output_path = os.path.join(base_dir, "applications", company_dir)
    os.makedirs(output_path, exist_ok=True)
    
    return output_path

def generate_filename(role_name, file_type):
    """Generate filename following convention: Dinesh_Chhantyal_Resume_PositionTitle.pdf"""
    # Clean role name for filename
    position_title = role_name.replace(' ', '').replace('/', '').replace('\\', '').replace('&', 'and')
    
    if file_type.lower() == 'resume':
        return f"Dinesh_Chhantyal_Resume_{position_title}.pdf"
    elif file_type.lower() == 'coverletter':
        return f"Dinesh_Chhantyal_CoverLetter_{position_title}.pdf"
    else:
        return f"Dinesh_Chhantyal_{file_type}_{position_title}.pdf"

def cli_main():
    base_dir = os.getcwd()
    company_name = get_company_name()
    role_name = get_role_name()
    job_url = get_job_description_url()

    # Create organized output directory
    output_dir = create_output_structure(base_dir, company_name, role_name)

    # Save job description if provided
    if job_url:
        with open(os.path.join(output_dir, 'job_description.txt'), 'w') as f:
            f.write(f"URL: {job_url}\n\n")
            # TODO: Add job description scraping

    choice = get_user_choice()

    # Generate documents based on user choice
    if choice in ['1', '3']:
        resume_filename = generate_filename(role_name, 'resume')
        resume_file = os.path.join(output_dir, resume_filename)
        resume_generator = ResumeGenerator(os.path.join(base_dir, "resume", "resume.yml"))
        output_file = resume_generator.generate_pdf(resume_file, output_dir)
        print(f"\nResume generated: {output_file}")

    if choice in ['2', '3']:
        coverletter_filename = generate_filename(role_name, 'coverletter')
        cover_letter_file = os.path.join(output_dir, coverletter_filename)
        coverletter_generator = CoverLetterGenerator(os.path.join(base_dir, "coverletter", "coverletter.yml"))
        output_file = coverletter_generator.generate_pdf(cover_letter_file, output_dir, company_name)
        print(f"\nCover letter generated: {output_file}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', action='store_true', help='Launch GUI version')
    args = parser.parse_args()

    if args.ui:
        try:
            from ui import main as ui_main
            ui_main()
        except ImportError as e:
            print("\nError: PyQt6 is not properly installed.")
            print("Please run: pip install PyQt6 PyQt6-Qt6 PyQt6-sip")
            print(f"Original error: {str(e)}")
        except Exception as e:
            print(f"\nFailed to start UI: {str(e)}")
    else:
        cli_main()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
