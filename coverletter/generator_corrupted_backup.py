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

        # Clean up the website URL for display
        website_display = personal['homepage'].replace('https://www.', '').replace('https://', '')
        
        latex_content = f"""\\documentclass[12pt, letterpaper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage{{hyperref}}
\\usepackage{{setspace}}
\\usepackage{{xcolor}}
\\usepackage{{tikz}}
\\usetikzlibrary{{shapes.geometric, positioning}}

% Define professional colors
\\definecolor{{primaryyellow}}{{RGB}}{{255, 193, 7}}
\\definecolor{{accentorange}}{{RGB}}{{255, 152, 0}}
\\definecolor{{lightblue}}{{RGB}}{{74, 144, 226}}
\\definecolor{{softgray}}{{RGB}}{{240, 240, 240}}

% Remove page numbers
\\pagenumbering{{gobble}}

% Hyperlink styling - minimal for professional appearance
\\hypersetup{{
    colorlinks=false,
    pdfborder={{0 0 0}}
}}

% Balanced formatting - not too tight, not too loose
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{8pt}}
\\setlength{{\\baselineskip}}{{13pt}}
\\singlespacing
\\raggedright

\\begin{{document}}

% Professional letterhead banner header
\\begin{{tikzpicture}}[remember picture,overlay]
% Main header banner
\\fill[primaryyellow] (current page.north west) rectangle ([yshift=-1.5cm]current page.north east);
% Subtle accent line
\\fill[accentorange] ([yshift=-1.5cm]current page.north west) rectangle ([yshift=-1.6cm]current page.north east);
\\end{{tikzpicture}}

% Header content in banner
\\begin{{tikzpicture}}[remember picture,overlay]
\\node[anchor=north west, text=black, font=\\Large\\bfseries] at ([xshift=1in, yshift=-0.4cm]current page.north west) {{{personal['name']}}};
\\node[anchor=north west, text=black, font=\\footnotesize] at ([xshift=1in, yshift=-0.75cm]current page.north west) {{{personal['address']['line']}, {personal['address']['postal_code']}, {personal['address']['country']}}};
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-0.6cm]current page.north east) {{{personal['phone']['mobile']}}};
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-0.85cm]current page.north east) {{\\href{{mailto:{personal['email']}}}{{{personal['email']}}}}};
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-1.1cm]current page.north east) {{\\href{{{personal['homepage']}}}{{{website_display}}}}};
\\end{{tikzpicture}}

% Professional footer
\\begin{{tikzpicture}}[remember picture,overlay]
\\fill[softgray, opacity=0.3] ([yshift=0.8cm]current page.south west) rectangle (current page.south east);
\\node[anchor=south, text=gray, font=\\tiny] at ([yshift=0.4cm]current page.south) {{Professional correspondence from {personal['name']} | {personal['phone']['mobile']} | {personal['email']}}};
\\end{{tikzpicture}}

\\vspace{{2cm}}

% Date (flush left)
\\noindent {letter['date']}

\\vspace{{6pt}}

% Recipient information (flush left)
\\noindent {recipient['name']}\\\\
{recipient.get('title', '')}\\\\
{recipient['company']}\\\\
{recipient['address']}

\\vspace{{6pt}}

% Salutation with colon (professional)
\\noindent {letter['opening']}:

\\vspace{{6pt}}

% Body paragraphs with balanced spacing
{self.format_body_paragraphs(letter['body'])}

\\vspace{{12pt}}

% Complimentary close with comma
Sincerely,

\\vspace{{18pt}}

% Typed name (clean, no abstract shapes)
{personal['name']}

\\end{{document}}
"""
        return latex_content

    def save_cover_letter(self, output_file_path, company_name):
\definecolor{accentorange}{RGB}{255, 152, 0}
\definecolor{lightblue}{RGB}{74, 144, 226}
\definecolor{softgray}{RGB}{240, 240, 240}

% Remove page numbers
\pagenumbering{gobble}

% Hyperlink styling - minimal for professional appearance
\hypersetup{
    colorlinks=false,
    pdfborder={0 0 0}
}

% Balanced formatting - not too tight, not too loose
\setlength{\parindent}{0pt}
\setlength{\parskip}{8pt}
\setlength{\baselineskip}{13pt}
\singlespacing
\raggedright

\begin{document}

% Professional letterhead banner header
\\begin{{tikzpicture}}[remember picture,overlay]
% Main header banner
\\fill[primaryyellow] (current page.north west) rectangle ([yshift=-1.5cm]current page.north east);
% Subtle accent line
\\fill[accentorange] ([yshift=-1.5cm]current page.north west) rectangle ([yshift=-1.6cm]current page.north east);
\\end{{tikzpicture}}

% Header content in banner
\\begin{{tikzpicture}}[remember picture,overlay]
\\node[anchor=north west, text=black, font=\\Large\\bfseries] at ([xshift=1in, yshift=-0.4cm]current page.north west) {{{personal['name']}}};
\\node[anchor=north west, text=black, font=\\footnotesize] at ([xshift=1in, yshift=-0.75cm]current page.north west) {{{personal['address']['line']}, {personal['address']['postal_code']}, {personal['address']['country']}}};
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-0.6cm]current page.north east) {{{personal['phone']['mobile']}}};
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-0.85cm]current page.north east) {{\\href{{mailto:{personal['email']}}}{{{personal['email']}}}}}; 
\\node[anchor=north east, text=black, font=\\footnotesize] at ([xshift=-1in, yshift=-1.1cm]current page.north east) {{\\href{{{personal['homepage']}}}{{{personal['homepage'].replace('https://www.', '')}}}}};
\\end{{tikzpicture}}

% Professional footer
\\begin{{tikzpicture}}[remember picture,overlay]
\\fill[softgray, opacity=0.3] ([yshift=0.8cm]current page.south west) rectangle (current page.south east);
\\node[anchor=south, text=gray, font=\\tiny] at ([yshift=0.4cm]current page.south) {{Professional correspondence from {personal['name']} | {personal['phone']['mobile']} | {personal['email']}}};
\\end{{tikzpicture}}

\\vspace{{2cm}}

% Date (flush left)
\\noindent {letter['date']}

\\vspace{{6pt}}

% Recipient information (flush left)
\\noindent {recipient['name']}\\\\
{recipient.get('title', '')}\\\\
{recipient['company']}\\\\
{recipient['address']}

\\vspace{{6pt}}

% Salutation with colon (professional)
\\noindent {letter['opening']}:

\\vspace{{6pt}}

% Body paragraphs with balanced spacing
{self.format_body_paragraphs(letter['body'])}

\\vspace{{12pt}}

% Complimentary close with comma
Sincerely,

\\vspace{{18pt}}

% Typed name (clean, no abstract shapes)
{personal['name']}
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
