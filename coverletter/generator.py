from datetime import datetime
import os
import subprocess
import yaml
from generators.base import DocumentGenerator


class CoverLetterGenerator(DocumentGenerator):
    def __init__(self, yaml_file):
        super().__init__(yaml_file)

    def generate_cover_letter(self):
        personal = self.data["personal_information"]
        recipient = self.data["recipient"]
        letter = self.data["letter"]

        cover_letter = f"""
        {personal['name']}
        {personal.get('title', '')}
        {personal['address']['line']}, {personal['address']['postal_code']}, {personal['address']['country']}
        Mobile: {personal['phone']['mobile']}
        Fixed: {personal['phone'].get('fixed','')}
        Fax: {personal['phone'].get('fax','')}
        Email: {personal['email']}
        Homepage: {personal['homepage']}
        Extra Info: {personal.get('extra_info','')}
        Quote: {personal.get('quote','')}

        To: {recipient['name']}
        Address: {recipient['address']}

        Date: {letter['date']}
        {letter['opening']}

        {letter['body']}

        {letter['closing']}
        Enclosure: {letter['enclosure']}
        """
        return cover_letter.strip()

    def format_body_paragraphs(self, body_text):
        """Format body paragraphs with proper spacing for readability"""
        paragraphs = body_text.strip().split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            # Clean up the paragraph and add proper formatting
            clean_paragraph = paragraph.strip().replace('\n', ' ')
            formatted_paragraphs.append(clean_paragraph)
        
        # Join paragraphs with better spacing for readability
        return '\n\n'.join(formatted_paragraphs)

    def replace_placeholders(self, company_name):
        """
        Interactively ask user for missing placeholder values in the YAML data.
        Only prompts for values that contain placeholder text.
        """
        data = self.data.copy()
        # Escape LaTeX special characters
        data["letter"]["body"] = data["letter"]["body"].replace("%", "\\%").replace("&", "\\&")
        if "[Hiring Manager's Name]" in data["recipient"]["name"]:
            manager_name = input("Enter hiring manager's name: ").strip()
            data["recipient"]["name"] = data["recipient"]["name"].replace(
                "[Hiring Manager's Name]", manager_name
            )
        if "[Company Address]" in data["recipient"]["address"]:
            company_address = input("Enter company address: ").strip()
            data["recipient"]["address"] = data["recipient"]["address"].replace(
                "[Company Address]", company_address
            )
        if "[Company Name]" in data["recipient"]["address"]:
            data["recipient"]["address"] = data["recipient"]["address"].replace(
                "[Company Name]", company_name
            )
        # Escape special characters in recipient information
        data["recipient"]["title"] = data["recipient"]["title"].replace("&", "\\&")
        data["letter"]["date"] = datetime.now().strftime("%Y-%m-%d")
        data["letter"]["opening"] = data["letter"]["opening"].replace(
            "[Company Name]", company_name
        )
        data["letter"]["body"] = data["letter"]["body"].replace(
            "[Company Name]", company_name
        )
        self.data = data
        return data

    def generate_tex(self, company_name):
        self.replace_placeholders(company_name)
        personal = self.data["personal_information"]
        recipient = self.data["recipient"]
        letter = self.data["letter"]

        content = [
            r"""
\documentclass[12pt, letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=1in]{geometry}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{hyperref}
\usepackage{setspace}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, positioning}

% Define professional theme colors (matching your website)
\definecolor{darkblue}{RGB}{15, 23, 42}
\definecolor{accentorange}{RGB}{251, 146, 60}
\definecolor{lightgray}{RGB}{148, 163, 184}
\definecolor{white}{RGB}{255, 255, 255}
\definecolor{textgray}{RGB}{71, 85, 105}

% Remove page numbers
\pagenumbering{gobble}

% Hyperlink styling - minimal for professional appearance
\hypersetup{
    colorlinks=false,
    pdfborder={0 0 0}
}

% Compact document formatting to fit on one page
\setlength{\parindent}{0pt}
\setlength{\parskip}{9pt}
\setlength{\baselineskip}{14pt}
\setstretch{1.1}
\raggedright

\begin{document}

% Clean, professional header with excellent typography
\begin{tikzpicture}[remember picture,overlay]
% Clean header background
\fill[darkblue] (current page.north west) rectangle ([yshift=-2.3cm]current page.north east);
% Elegant accent line
\fill[accentorange] ([yshift=-2.3cm]current page.north west) rectangle ([yshift=-2.4cm]current page.north east);

% Professional layout: Name larger, contact info smaller and grouped
\node[anchor=west, text=white, inner sep=0pt] at ([xshift=1in, yshift=-0.8cm]current page.north west) {
\fontsize{24}{28}\selectfont\bfseries """ + personal['name'] + r"""
};

% Consolidated contact info - all on one line for cleaner look
\node[anchor=west, text=white, inner sep=0pt] at ([xshift=1in, yshift=-1.5cm]current page.north west) {
\fontsize{9.5}{11}\selectfont """ + personal['phone']['mobile'] + r""" $\cdot$ """ + personal['email'] + r""" $\cdot$ """ + personal['homepage'].replace('https://www.', '').replace('https://', '') + r""" $\cdot$ """ + personal['address']['line'] + r"""
};
\end{tikzpicture}

\vspace{0.7cm}""",
            f"""
% Date
\\noindent {letter['date']}

\\vspace{{12pt}}

% Recipient information (flush left)
\\noindent {recipient['name']}\\\\
{recipient.get('title', '')}\\\\
{recipient['company']}\\\\
{recipient['address']}

\\vspace{{6pt}}

% Salutation with colon (no extra space after)
\\noindent {letter['opening']}:

% Body paragraphs with clean spacing
{self.format_body_paragraphs(letter['body'])}

\\vspace{{12pt}}

% Clean signature section
Sincerely,

\\vspace{{48pt}}

{personal['name']}

% Yellow footer strip at bottom of page
\\begin{{tikzpicture}}[remember picture,overlay]
\\fill[accentorange] ([yshift=0.5cm]current page.south west) rectangle ([yshift=0.6cm]current page.south east);
\\end{{tikzpicture}}
""",
            r"\end{document}",
        ]

        return "\n".join(content)

    def save_cover_letter(self, output_file_path, company_name):
        output_dir = os.path.dirname(output_file_path)
        os.makedirs(output_dir, exist_ok=True)
        
        tex_content = self.generate_tex(company_name)
        base_name = os.path.splitext(output_file_path)[0]
        tex_file = base_name + ".tex"
        
        with open(tex_file, "w", encoding="utf-8") as tex:
            tex.write(tex_content)
        return tex_file

    def generate_pdf(self, output_file_path, output_dir, company_name):
        try:
            tex_file = self.save_cover_letter(output_file_path, company_name)
            pdf_file = self.compile_pdf(tex_file, output_dir)
            os.remove(tex_file)
            return pdf_file
        except Exception as e:
            print(f"Failed to generate PDF: {str(e)}")
            raise

    def compile_pdf(self, tex_file, output_dir):
        try:
            output_dir = os.path.dirname(tex_file)
            # Try to find pdflatex in common locations
            pdflatex_paths = [
                "pdflatex",  # If it's in PATH
                "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
                "/usr/local/texlive/2024/bin/x86_64-darwin/pdflatex",
                "/Library/TeX/texbin/pdflatex",
            ]

            pdflatex_cmd = None
            for path in pdflatex_paths:
                if os.path.exists(path) or path == "pdflatex":
                    try:
                        subprocess.run(
                            [path, "--version"], check=True, capture_output=True
                        )
                        pdflatex_cmd = path
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            if not pdflatex_cmd:
                raise Exception(
                    "pdflatex not found. Please install LaTeX (MacTeX) or add it to PATH"
                )

            for _ in range(2):
                result = subprocess.run(
                    [
                        pdflatex_cmd,
                        "-interaction=nonstopmode",
                        "-output-directory=" + output_dir,
                        tex_file,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(result.stdout)
                    print(result.stderr)
            base_name = os.path.splitext(tex_file)[0]
            for ext in [".aux", ".log", ".out"]:
                aux_file = base_name + ext
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            pdf_file = base_name + ".pdf"
            if os.path.exists(pdf_file):
                return pdf_file
            raise Exception("PDF file was not generated")
        except Exception as e:
            raise Exception(f"Failed to generate PDF: {str(e)}")


# Example Usage
# generator = CoverLetterGenerator('cover_letter.yml')
# print(generator.generate_cover_letter())
