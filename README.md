# Gmail Summarizer README

## Overview
This project processes emails in your Gmail inbox, summarizes them using OpenAI's large language model, and converts the summary into an audio MP3 file using Google Cloud Text-to-Speech (TTS). 

The program is terminal-based and requires setting up Google Cloud and Gmail API authentication, as well as providing an OpenAI API key.

At the end I have included a segment on how I would improve this project if I were to revisit it.

---

## Example Output
**Text Output**

![Screenshot 2024-11-21 213804](https://github.com/user-attachments/assets/caac3b0a-b651-47af-b182-459226a70c7a)

**Audio Output**

https://github.com/user-attachments/assets/ff089995-1b37-4015-ab7e-6177c01b1190

---

## Prerequisites

1. **Python Environment**:
   - Ensure you have Python 3.7 or above installed.
   - Install the required libraries using the following command:
     ```bash
     pip install -r requirements.txt
     ```
     
2. **Google Cloud Project Setup**:
   - Set up a Google Cloud project for Gmail API access and Text-to-Speech API.

3. **Gmail API and Authentication**:
   - Create a credentials JSON file for Gmail API.

4. **Google Cloud Text-to-Speech**:
   - Create a service account and generate a key JSON file.

5. **OpenAI API Key**:
   - Obtain an API key from OpenAI.

6. **Directory Structure**:
   - Place credentials files in the appropriate directories:
     ```
     BASE_DIR/
     ├── GmailSummarizer.py
     ├── credentials.json
     ├── key/
     │   └── <service-account-key>.json
     ```

---

## Setup Guide

### Step 1: Set the Base Directory
In the main Python script, set the `BASE_DIR` variable to your project's directory path. For example:
```python
BASE_DIR = 'C:\\Users\\your-username\\Desktop\\GmailSummarizer\\'
```

---

### Step 2: Setting Up Gmail API

1. **Enable Gmail API**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create or select an existing project.
   - Search for and enable the **Gmail API**.

2. **Create OAuth 2.0 Credentials**:
   - In the **Credentials** tab, create an **OAuth 2.0 Client ID**.
   - Download the `credentials.json` file and place it in the project's main directory (`BASE_DIR`).

3. **Authenticate Gmail**:
   - Run the script once to initiate the authentication process:
     ```bash
     python GmailSummarizer.py
     ```
   - During this process:
     - A browser will open for you to log in and grant access to your Gmail account.
     - A `token.json` file will be generated and saved in the main directory.

---

### Step 3: Setting Up Google Cloud Text-to-Speech

1. **Enable Text-to-Speech API**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Search for and enable the **Cloud Text-to-Speech API**.

2. **Create a Service Account**:
   - In the **IAM & Admin** section, create a new service account.
   - Assign the role `Text-to-Speech Admin` to the service account.

3. **Generate and Save Key**:
   - Generate a JSON key file for the service account.
   - Save the file in a subdirectory called `key` within the project directory.
     Example path:
     ```
     BASE_DIR/key/<service-account-key>.json
     ```

4. **Update Service Account Path**:
   - In the script, update the `SERVICE_ACCOUNT_PATH` variable:
     ```python
     SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, 'key\\<service-account-key>.json')
     ```

---

### Step 4: Add OpenAI API Key

1. **Obtain OpenAI API Key**:
   - Sign up for an account on [OpenAI](https://platform.openai.com/).
   - Retrieve your API key from the OpenAI dashboard.

2. **Add API Key to the Script**:
   - Replace `<your-api-key>` in the script with your actual OpenAI API key:
     ```python
     client = OpenAI(api_key='<your-api-key>')
     ```

---

### Step 5: Run the Script

1. **Launch the Script**:
   - Open a terminal and navigate to the project directory.
   - Run the following command:
     ```bash
     python GmailSummarizer.py
     ```

2. **Workflow Overview**:
   The script provides a menu-driven interface with several options. Here's the recommended workflow:
   - **Step 1: Update Emails**:
     - Select the option to **Update Emails**.
     - This action retrieves emails from your Gmail inbox based on the configured timeframe (default: last 24 hours).
   - **Step 2: Get Text Summary**:
     - After updating emails, select the option to **Get Text Summary**.
     - This generates a summarized version of the gathered emails.
     - The text summary will be saved in the output directory.
   - **Step 3: Get Audio Summary**:
     - Once you have the text summary, choose **Get Audio Summary**.
     - This converts the text summary into a script and generates an MP3 file using Google Cloud Text-to-Speech.
     - The audio file will be saved in the output directory.

3. **Additional Features**:
   - **Adjust Settings**:
     - Use the **Settings** menu to change the email retrieval timeframe (e.g., include emails older than 24 hours).
   - **Fix Gmail Authentication**:
     - If you encounter issues with Gmail authentication, use the **Fix Gmail Link** option to refresh your credentials.

4. **Output**:
   - After completing the steps, check the output directory for:
     - The summarized text file.
     - The generated MP3 file.

---

### How I Would Improve the Project

This project was created a few months ago, and since then, my coding skills have improved significantly. If I were to revisit this project, these are the changes I would make to enhance its functionality, efficiency, and user experience:

1. **Code Refactoring**:
   - The current code structure could benefit from improved readability and efficiency.
   - I would apply modern coding practices, such as better modularization, error handling, and documentation, to make the codebase cleaner and easier to maintain.

2. **Enhanced File Structure**:
   - Instead of a monolithic script, I would reorganize the project into multiple smaller files with specific functionality, such as:
     - **`email_handler.py`**: For Gmail API interactions.
     - **`summarizer.py`**: For processing and summarizing emails.
     - **`text_to_speech.py`**: For converting summaries to audio.
     - **`main.py`**: To act as the entry point and coordinate other modules.

3. **Improved Frontend**:
   - Currently, the project is terminal-based, which can be intimidating for non-technical users.
   - I would develop a simple graphical user interface (GUI) to make the tool more accessible. For example:
     - A desktop application using frameworks like **Tkinter** or **PyQt**.
     - A web-based interface for easier interaction.

4. **Streamlined Pipeline**:
   - I would redesign the workflow to be more user-friendly:
     - Combine the steps into a single process triggered by a single click or command.
     - Automate intermediate steps like email updates and text summarization.
     - Provide clear real-time feedback on progress (e.g., “Fetching emails...”, “Generating summary...”).

5. **Improved Audio Output**:
   - I would enhance the quality of the audio output by utilizing a Text-to-Speech model that supports **SSML (Speech Synthesis Markup Language)**.
   - Fully implementing SSML formatting in the code would allow for advanced control over speech patterns, such as:
     - Adding appropriate pause breaks between sections.
     - Emphasizing key phrases.
     - Adjusting the tone and rhythm for a more natural and engaging audio experience.

6. **Cost-Effective API Usage**:
   - To optimize the cost of OpenAI API usage, I would:
     - Scale the token usage for email summaries based on the character count of the email body and other variables (e.g., importance, length, or user-selected criteria).

7. **Additional Features**:
   - Add support for filtering emails by specific labels or keywords, enabling more tailored summaries.
   - Include more customization options for the summary and audio output, such as selecting voice types, languages, or tones.

---
