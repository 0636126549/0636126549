import argparse
import os
import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from fpdf import FPDF
import yagmail


REQUIRED_COLUMNS = ["Company", "Email", "JobTitle"]
DEFAULT_OUTPUT_DIR = "generated_docs"
DEFAULT_LOG_FILE = "email_log.xlsx"


@dataclass
class Config:
    email_address: str
    email_password: str
    master_cv: str
    cover_letter_template: str
    spreadsheet: str
    log_file: str = DEFAULT_LOG_FILE
    output_dir: str = DEFAULT_OUTPUT_DIR
    sender_name: str = "Your Name"
    dry_run: bool = False


def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned[:80] or "unknown"


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


def create_pdf(text: str, output_dir: str, filename: str) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, text)

    output_path = os.path.join(output_dir, filename)
    pdf.output(output_path)
    return output_path


def validate_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Spreadsheet is missing required columns: {', '.join(missing)}"
        )


def personalized_cover_letter(
    template_text: str,
    company: str,
    job_title: str,
    custom_message: Optional[str],
) -> str:
    cover_text = template_text.format(Company=company, JobTitle=job_title)
    if custom_message and str(custom_message).strip():
        cover_text += f"\n\n{custom_message}"
    return cover_text


def build_email_body(company: str, sender_name: str) -> str:
    return (
        f"Dear Hiring Manager at {company},\n\n"
        "Please find attached my CV and cover letter for your consideration.\n\n"
        f"Best regards,\n{sender_name}"
    )


def load_dataframe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Spreadsheet file not found: {path}")

    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def send_applications(config: Config) -> str:
    os.makedirs(config.output_dir, exist_ok=True)

    df = load_dataframe(config.spreadsheet)
    validate_columns(df)

    if "Status" not in df.columns:
        df["Status"] = ""
    if "Error" not in df.columns:
        df["Error"] = ""

    master_cv_text = read_text_file(config.master_cv)
    cover_template_text = read_text_file(config.cover_letter_template)

    yag = None
    if not config.dry_run:
        yag = yagmail.SMTP(config.email_address, config.email_password)

    for index, row in df.iterrows():
        company = str(row["Company"]).strip()
        recipient = str(row["Email"]).strip()
        job_title = str(row["JobTitle"]).strip()
        custom_message = row.get("CustomMessage", "")

        safe_company = sanitize_filename(company)

        personalized_cv_text = f"Dear {company} Hiring Team,\n\n{master_cv_text}"
        cv_filename = f"CV_{index}_{safe_company}.pdf"
        cv_pdf = create_pdf(personalized_cv_text, config.output_dir, cv_filename)

        cover_text = personalized_cover_letter(
            cover_template_text,
            company=company,
            job_title=job_title,
            custom_message=custom_message,
        )
        cover_filename = f"CoverLetter_{index}_{safe_company}.pdf"
        cover_pdf = create_pdf(cover_text, config.output_dir, cover_filename)

        email_body = build_email_body(company, config.sender_name)

        try:
            if config.dry_run:
                df.at[index, "Status"] = "Dry run"
                print(f"[DRY RUN] Prepared documents for {recipient}")
                continue

            assert yag is not None
            yag.send(
                to=recipient,
                subject=f"Application for {job_title} at {company}",
                contents=email_body,
                attachments=[cv_pdf, cover_pdf],
            )
            df.at[index, "Status"] = "Sent"
            df.at[index, "Error"] = ""
            print(f"[SUCCESS] Email sent to {recipient}")
        except Exception as exc:  # noqa: BLE001
            df.at[index, "Status"] = "Failed"
            df.at[index, "Error"] = str(exc)
            print(f"[FAILED] Could not send to {recipient}: {exc}")

    df.to_excel(config.log_file, index=False)
    return config.log_file


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="Generate personalized CV/cover-letter PDFs and send job application emails."
    )
    parser.add_argument("--email-address", required=True)
    parser.add_argument("--email-password", required=True)
    parser.add_argument("--master-cv", default="MasterCV.txt")
    parser.add_argument("--cover-template", default="CoverLetterTemplate.txt")
    parser.add_argument("--spreadsheet", default="companies.xlsx")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sender-name", default="Your Name")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate files and log output without sending emails.",
    )

    args = parser.parse_args()
    return Config(
        email_address=args.email_address,
        email_password=args.email_password,
        master_cv=args.master_cv,
        cover_letter_template=args.cover_template,
        spreadsheet=args.spreadsheet,
        log_file=args.log_file,
        output_dir=args.output_dir,
        sender_name=args.sender_name,
        dry_run=args.dry_run,
    )


def main() -> None:
    config = parse_args()
    log_path = send_applications(config)
    print(f"Done. Log saved to {log_path}")


if __name__ == "__main__":
    main()
