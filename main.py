from datetime import datetime
import os
import sys
import shutil
import yaml
from resume.generator import ResumeGenerator
from coverletter.generator import CoverLetterGenerator


def create_output_structure(base_dir, company_name):
    """Create output directory: applications/COMPANY/"""
    company_dir = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    output_path = os.path.join(base_dir, "applications", company_dir)
    os.makedirs(output_path, exist_ok=True)
    return output_path


def read_candidate_name(yaml_path, default="Candidate"):
    """Read the candidate name from a resume/profile YAML for filenames."""
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}
        block = data.get('personal') or data.get('personal_information') or {}
        return block.get('name', default) or default
    except Exception:
        return default


def generate_filename(role_name, file_type, candidate_name="Candidate"):
    """Generate filename: CandidateName_Resume_PositionTitle"""
    position_title = role_name.replace(' ', '').replace('/', '').replace('\\', '').replace('&', 'and')
    name = candidate_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    return f"{name}_{file_type.capitalize()}_{position_title}"


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate a one-page resume and cover letter PDF from your YAML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow:
  The resume-builder agent edits resume/resume.yml to match a job description.
  Then render the PDF:
    python main.py --company "Example Corp" --role "Software Engineer" --type both

  --type resume       Resume only
  --type coverletter  Cover letter only
  --type both         Both (default when omitted)
        """
    )
    parser.add_argument('--ui', action='store_true', help='Launch the GUI version')
    parser.add_argument('--company', type=str, required=False, help='Company name')
    parser.add_argument('--role', type=str, required=False, help='Role title')
    parser.add_argument('--type', type=str, choices=['resume', 'coverletter', 'both'],
                        default='both', help='What to generate (default: both)')
    parser.add_argument('--url', type=str, default='', help='Job description URL (optional, saved for reference)')
    args = parser.parse_args()

    if args.ui:
        try:
            from ui import main as ui_main
            ui_main()
        except ImportError as e:
            print(f"\nError: PyQt6 is not properly installed. {e}")
        return

    if not args.company:
        parser.error("--company is required. Example: --company 'Example Corp'")
    if not args.role:
        parser.error("--role is required. Example: --role 'Software Engineer'")

    base_dir = os.getcwd()
    output_dir = create_output_structure(base_dir, args.company)

    if args.url:
        with open(os.path.join(output_dir, 'job_description.txt'), 'w') as f:
            f.write(f"URL: {args.url}\n\n")

    # --- RESUME ---
    if args.type in ['resume', 'both']:
        base_resume = os.path.join(base_dir, "resume", "resume.yml")
        if not os.path.exists(base_resume):
            print(f"Error: resume not found at {base_resume}")
            sys.exit(1)

        candidate_name = read_candidate_name(base_resume)
        # Keep a copy of the resume used for this application
        shutil.copy2(base_resume, os.path.join(output_dir, "resume.yml"))

        base_name = generate_filename(args.role, 'Resume', candidate_name)
        tex_file = os.path.join(output_dir, base_name + ".tex")

        resume_generator = ResumeGenerator(base_resume)
        output_file = resume_generator.generate_pdf(tex_file, output_dir)
        print(f"\nResume generated: {output_file}")

    # --- COVER LETTER ---
    if args.type in ['coverletter', 'both']:
        base_cover = os.path.join(base_dir, "coverletter", "coverletter.yml")
        if not os.path.exists(base_cover):
            print(f"Error: cover letter not found at {base_cover}")
            sys.exit(1)

        candidate_name = read_candidate_name(base_cover)
        base_name = generate_filename(args.role, 'CoverLetter', candidate_name)
        cover_letter_file = os.path.join(output_dir, base_name + ".tex")

        coverletter_generator = CoverLetterGenerator(base_cover)
        output_file = coverletter_generator.generate_pdf(cover_letter_file, output_dir, args.company)
        print(f"\nCover letter generated: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
