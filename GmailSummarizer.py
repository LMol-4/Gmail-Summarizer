# Author - Luke Molony
# Date - 2/8/2024

import os
import base64
import json
import re
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient import errors
from googleapiclient.http import BatchHttpRequest
from google.cloud import texttospeech
from openai import OpenAI
from pathlib import Path
from bs4 import BeautifulSoup
import quopri

BASE_DIR = 'C:\\Users\\example\\Desktop\\GmailSummarizer\\' # ADD YOUR BASE DIRECTORY HERE

# Set up logging
log_file = os.path.join(BASE_DIR, 'app.log')
logging.basicConfig(
    filename=log_file,
    filemode='a', 
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Initialize the OpenAI client
client = OpenAI(api_key='API KEY HERE') # ADD YOUR OPEN AI API KEY HERE

# Base paths
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, 'key\\UPDATE THIS FILE NAME.json') # MAKE SURE TO UPDATE TO YOUR FILENAME
EMAILS_JSON_PATH = os.path.join(BASE_DIR, 'emails.json')
EMAILS_SUBDIR = os.path.join(BASE_DIR, 'emails')

# Output paths
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
SUMMARY_FILE_PATH = os.path.join(OUTPUT_DIR, 'email_summary.txt')
TTS_OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, 'formatted_summary.txt')
SSML_OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, 'formatted_summary.ssml')

# Audio output
TTS_AUDIO_OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, 'email_summary.mp3')


# Ensure output directories exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    logging.info(f"Created output directory: {OUTPUT_DIR}")

if not os.path.exists(EMAILS_SUBDIR):
    os.makedirs(EMAILS_SUBDIR)
    logging.info(f"Created emails subdirectory: {EMAILS_SUBDIR}")

#Clear the terminal screen based on the operating system.
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

#Display the menu and return the user's choice.
def display_menu(menu_title, options):
    logging.info(f"Displaying menu: {menu_title}")
    print(f"{menu_title}\n")
    for i, option in enumerate(options, start=1):
        print(f"{i}) {option}")

    while True:
        menu_input = input("\nPlease select an option: ")
        if menu_input.isdigit() and 1 <= int(menu_input) <= len(options):
            logging.info(f"User selected option {menu_input}")
            return int(menu_input)
        else:
            logging.warning(f"Invalid input: {menu_input}")
            print("Invalid input. Please try again.")

def main_menu():
    options = ["Get Text Summary", "Get Audio Summary", "Update Emails", "Settings", "Quit"]
    return display_menu("Email Summarizer", options)

def settings_menu():
    options = ["Change Timeframe", "Fix GMAIL link issues", "Go Back"]
    return display_menu("Settings", options)

def timeframe_menu():
    options = ["Past 24 Hours", "Past 48 Hours", "Past 72 Hours"]
    return display_menu("Select Timeframe", options)

# Authenticate google token
def gmail_authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        logging.info("No valid credentials, starting authentication flow...")
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing credentials...")
            creds.refresh(Request())
        else:
            logging.info("Starting OAuth flow using credentials.json")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(os.path.join(BASE_DIR, 'credentials.json'), SCOPES)
                creds = flow.run_local_server(port=8080)
                logging.info("Authentication complete.")
            except Exception as e:
                logging.error(f"Error during OAuth flow: {e}")
                return None

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            logging.info(f"Credentials saved to {TOKEN_PATH}")

    return creds


# Function to fetch emails within a specified timeframe
def get_emails_within_timeframe(service, hours):
    today = datetime.now()
    timeframe = today - timedelta(hours=hours)
    query = f"after:{int(timeframe.timestamp())}"

    logging.info(f"Fetching emails within {hours} hours timeframe...")
    email_data = []

    try:
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])

        if not messages:
            logging.info("No emails found.")
            return email_data

        logging.info(f"Fetched {len(messages)} email message IDs.")
        batch = service.new_batch_http_request()

        def handle_batch_response(request_id, response, exception):
            if exception:
                logging.error(f"Error fetching message {request_id}: {exception}")
            else:
                email_data.append(process_email(response))

        # Add each message request to the batch
        for msg in messages:
            batch.add(
                service.users().messages().get(userId='me', id=msg['id'], format='full'),
                callback=handle_batch_response
            )

        batch.execute()
        logging.info(f"Successfully fetched {len(email_data)} emails.")

    except Exception as error:
        logging.error(f"Error fetching emails: {error}")

    return email_data


# Helper function to process individual email message
def process_email(message):
    payload = message['payload']
    headers = {header['name']: header['value'] for header in payload.get('headers', [])}

    return {
        'id': message['id'],
        'from': headers.get('From', ''),
        'subject': headers.get('Subject', ''),
        'date': headers.get('Date', ''),
        'body': extract_email_body(payload)
    }

# Decodes the email body based on the encoding.
def decode_body(data, encoding='base64'):
    try:
        if encoding == 'base64':
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            return decoded
        elif encoding == 'quoted-printable':
            decoded = quopri.decodestring(data).decode('utf-8', errors='replace')
            return decoded
        else:
            logging.warning(f"Unexpected encoding: {encoding}")
    except Exception as e:
        logging.error(f"Error decoding body: {e}")
    return ""

# Recursively extract the email body, handling multiple MIME parts.
def extract_email_body(payload):
    def get_body_from_parts(parts):
        text_body, html_body = None, None

        for part in parts:
            if part.get('parts'):
                nested_text, nested_html = get_body_from_parts(part['parts'])
                text_body = text_body or nested_text
                html_body = html_body or nested_html
            else:
                mime_type = part.get('mimeType')
                body_data = part.get('body', {}).get('data', '')
                encoding = part.get('body', {}).get('encoding', 'base64')

                logging.info(f"Processing MIME type: {mime_type}")

                if mime_type == 'text/plain':
                    text_body = text_body or decode_body(body_data, encoding)
                elif mime_type == 'text/html':
                    html_body = html_body or decode_body(body_data, encoding)
                else:
                    logging.warning(f"Unexpected MIME type: {mime_type}")

        return text_body, html_body

    if not payload.get('parts'):
        body_data = payload.get('body', {}).get('data', '')
        mime_type = payload.get('mimeType', '')
        encoding = payload.get('body', {}).get('encoding', 'base64')

        logging.info(f"Single-part email with MIME type: {mime_type}")
        
        if mime_type == 'text/plain':
            return decode_body(body_data, encoding).strip()
        elif mime_type == 'text/html':
            soup = BeautifulSoup(decode_body(body_data, encoding), 'html.parser')
            return soup.get_text().strip()

    parts = payload.get('parts', [])
    text_body, html_body = get_body_from_parts(parts) if parts else (None, None)

    if html_body:
        soup = BeautifulSoup(html_body, 'html.parser')
        return soup.get_text().strip()

    return text_body.strip() if text_body else ""


# File Operations Helper
def save_to_json(filepath, data, message):
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        logging.info(message)
    except Exception as e:
        logging.error(f"Error saving to {filepath}: {e}")

# Replace excessive newlines and spaces
def strip_email_body(text):
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\r', ' '))
    return text.strip()


# Function to process and strip all emails
def strip_emails():
    emails = load_emails(EMAILS_JSON_PATH)
    logging.info(f"Loaded {len(emails)} emails from {EMAILS_JSON_PATH}")

    for email in emails:
        stripped_email = {
            'from': email.get('from'),
            'date': email.get('date'),
            'stripped_text': strip_email_body(email.get('body', ''))
        }

        date_str = email.get('date', '').replace(':', '-').replace(' ', '_')
        file_name = f"{date_str}.json"
        file_path = os.path.join(EMAILS_SUBDIR, file_name)

        save_to_json(file_path, stripped_email, f"Stripped email data saved to {file_path}")

# Function to save emails to JSON file
def save_emails_to_json(emails):
    try:
        with open(EMAILS_JSON_PATH, 'w', encoding='utf-8') as json_file:
            json.dump(emails, json_file, indent=4, ensure_ascii=False)
        logging.info(f"Emails saved to {EMAILS_JSON_PATH}")
    except Exception as e:
        logging.error(f"Error saving emails to JSON: {e}")

# Function to load emails from file
def load_emails(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        return emails
    except Exception as e:
        logging.error(f"Error loading emails from {file_path}: {e}")
        return []

# Summarize emails
def generate_summary(email_text, email_from, email_date):
    try:
        logging.debug("Generating summary for email")
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Use gpt 4o mini
            messages=[
                {"role": "system", "content": "You are an intelligent email assistant designed to summarize emails clearly and concisely."},
                {"role": "user", "content": f"""
                The following is an email. Summarize it in a structured format, adhering precisely to the template outlined below. Ensure clarity, brevity, and relevance in each section, and focus on extracting key actionable information. If you are including any quotes, quote directly.
                
                1. *Title*: Craft a short, specific title that reflects the main subject of the email.
                2. *Date and Sender*: The date the email was sent and by whom. This line should be formatted exactly like this Sender Email - Day/Month/Year
                3. *Email Summary*: Write a brief and concise summary of the main points discussed in the email, focusing on essential information. If the email is a newsletter, summarize the main stories or topics covered. This should only be a few sentences long.
                4. *Key Takeaways*: Bullet points that highlight specific actions, key points, or deadlines from the email. If the email is a newsletters this should be the keypoints from all the stories. This should be the biggest part of the whole summary. Roughly two sentences if needed.
                
                The email details are as follows:
                
                **From**: {email_from}
                **Date**: {email_date}
                **Content**: {email_text}
                """}
            ],
            max_tokens=300,  # Adjusted token limit for a more detailed summary
            temperature=0.4  # Low temperature for factual, clear summarization
        )
        
        summary = completion.choices[0].message.content
        logging.info("Summary generated successfully")
        return summary

    except Exception as e:
        logging.exception("Error generating summary")
        return None
    
def process_emails():
    email_files = [f for f in os.listdir(EMAILS_SUBDIR) if f.endswith('.json')]
    logging.info(f"Found {len(email_files)} email files to process")

    with open(SUMMARY_FILE_PATH, 'a', encoding='utf-8') as summary_file:
        for email_file in email_files:
            try:
                with open(os.path.join(EMAILS_SUBDIR, email_file), 'r', encoding='utf-8') as f:
                    email_data = json.load(f)

                    email_text = email_data.get('stripped_text', '')
                    email_from = email_data.get('from', 'Unknown sender')
                    email_date = email_data.get('date', 'Unknown date')

                    if email_text:
                        summary = generate_summary(email_text, email_from, email_date)

                        if summary:
                            summary_file.write(f"Email: {email_file}\nSummary:\n {summary}\n\n---\n")
                            logging.info(f"Summary for {email_file} written to {SUMMARY_FILE_PATH}")
                        else:
                            logging.warning(f"Could not generate summary for {email_file}")
                    else:
                        logging.warning(f"No text found in {email_file}, skipping...")
            except Exception as e:
                logging.error(f"Error processing {email_file}: {e}")

# Format email summaries for TTS.
def format_for_tts():
    if not os.path.exists(SUMMARY_FILE_PATH):
        logging.error(f"The summary file does not exist: {SUMMARY_FILE_PATH}")
        return

    with open(SUMMARY_FILE_PATH, 'r', encoding='utf-8') as summary_file:
        summaries = summary_file.read()

    logging.debug("Formatting email summaries for TTS")
    prompt = (
        "You are a personal assistant tasked with converting email summaries into an engaging narrative brief. Begin with a friendly greeting, then seamlessly summarize the most important points from each email in a conversational tone that feels like a relaxed chat. Highlight key information clearly and concisely, ensuring the reader easily grasps the main takeaways. When mentioning the sender or source of each email, weave it naturally into the narrative. If multiple emails discuss the same topic or share similar details, consolidate the information into a single, cohesive point, ensuring no repetition. Avoid including email dates or special characters (e.g., *, @, etc.). Focus on clarity and readability, keeping the entire brief within 4700 characters while emphasizing the essential details." + summaries
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": "You are a personal assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.4  
        )

        formatted_summary = completion.choices[0].message.content

        with open(TTS_OUTPUT_FILE_PATH, 'w', encoding='utf-8') as tts_file:
            tts_file.write(formatted_summary)

        logging.info(f"Formatted summary for TTS has been saved to {TTS_OUTPUT_FILE_PATH}")

    except Exception as e:
        logging.exception("Error generating formatted summary for TTS")

# Curently not being used, need to work on the ssml voices
def convert_text_to_ssml():
    if not os.path.exists(TTS_OUTPUT_FILE_PATH):
        logging.error(f"The original text file does not exist: {TTS_OUTPUT_FILE_PATH}")
        return

    with open(TTS_OUTPUT_FILE_PATH, 'r', encoding='utf-8') as file:
        text_content = file.read()

    ssml_content = f"<speak>\n\n{text_content}\n\n</speak>"

    with open(SSML_OUTPUT_FILE_PATH, 'w', encoding='utf-8') as ssml_file:
        ssml_file.write(ssml_content)
        logging.info(f"SSML content saved to: {SSML_OUTPUT_FILE_PATH}")

    return SSML_OUTPUT_FILE_PATH

def text_to_speech():
    if not os.path.exists(TTS_OUTPUT_FILE_PATH):
        logging.error(f"The TTS input file does not exist: {TTS_OUTPUT_FILE_PATH}")
        return

    with open(TTS_OUTPUT_FILE_PATH, 'r', encoding='utf-8') as file:
        text = file.read()

    client = texttospeech.TextToSpeechClient.from_service_account_file(SERVICE_ACCOUNT_PATH)

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-F",  # en-US-Journey-F
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE 
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3 
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(TTS_AUDIO_OUTPUT_FILE_PATH, 'wb') as output:
        output.write(response.audio_content)
        logging.info(f"TTS audio saved to: {TTS_AUDIO_OUTPUT_FILE_PATH}")


def main():
    exit_program = False
    creds = None
    service = None
    timeframe_hours = 24
    creds = gmail_authenticate()
    service = build('gmail', 'v1', credentials=creds)

    while not exit_program:
        clear_screen()
        current_menu = main_menu()

        if current_menu == 1:
            clear_screen()
            if os.path.exists(SUMMARY_FILE_PATH):
                os.remove(SUMMARY_FILE_PATH)
            process_emails()
        elif current_menu == 2:
            clear_screen()
            format_for_tts()
            #convert_text_to_ssml() # Currently not using - needs to be fixed for better voices.
            text_to_speech()
        elif current_menu == 3:
            clear_screen()
            if os.path.exists(EMAILS_JSON_PATH):
                os.remove(EMAILS_JSON_PATH)
                print(f"Deleted old {EMAILS_JSON_PATH}.")

            if service:
                print(f"Fetching emails from the past {timeframe_hours} hours...")
                emails = get_emails_within_timeframe(service, timeframe_hours)
                save_emails_to_json(emails)
                print(f"Fetched and saved {len(emails)} emails.")

                if os.path.exists(EMAILS_SUBDIR):
                    for file_name in os.listdir(EMAILS_SUBDIR):
                        file_path = os.path.join(EMAILS_SUBDIR, file_name)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception as e:
                            print(f"Failed to delete {file_name}: {e}")

                strip_emails()

                if os.path.exists(EMAILS_JSON_PATH):
                    os.remove(EMAILS_JSON_PATH)
                    print(f"{EMAILS_JSON_PATH} has been deleted after processing.")
            else:
                print("Please authenticate with Gmail first.")

        elif current_menu == 4:
            while True:
                clear_screen()
                submenu = settings_menu()

                if submenu == 1:
                    clear_screen()
                    selected_timeframe = timeframe_menu()
                    if selected_timeframe == 1:
                        timeframe_hours = 24
                    elif selected_timeframe == 2:
                        timeframe_hours = 48
                    elif selected_timeframe == 3:
                        timeframe_hours = 72
                    print(f"Timeframe set to the past {timeframe_hours} hours.")
                elif submenu == 2:
                    clear_screen()
                    creds = gmail_authenticate()
                    service = build('gmail', 'v1', credentials=creds)
                    print("Successfully linked to Gmail.")
                elif submenu == 3:
                    break
        elif current_menu == 5:
            print("Exiting the program. Goodbye!")
            exit_program = True

if __name__ == "__main__":
    main()