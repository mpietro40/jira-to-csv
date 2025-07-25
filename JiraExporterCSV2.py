from flask import (
    Flask,
    render_template,
    request,
    send_file,
    session,
    flash,
    redirect,
    url_for,
)
from jira import JIRA
import csv
import io
import os
import tempfile
import uuid
import threading
import time
import re
import html

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this"  # Change this to a secure secret key

chunk_size = 200
# NEW content to create temporary file and delete it
# Global dictionary to store temporary files
temp_files = {}
temp_files_lock = threading.Lock()


def cleanup_old_files():
    """Clean up temporary files older than 1 hour"""
    with temp_files_lock:
        current_time = datetime.now()
        files_to_remove = []

        for file_id, file_info in temp_files.items():
            if current_time - file_info["created"] > timedelta(hours=1):
                try:
                    if os.path.exists(file_info["path"]):
                        os.remove(file_info["path"])
                    files_to_remove.append(file_id)
                except:
                    pass

        for file_id in files_to_remove:
            del temp_files[file_id]


def connect_to_jira(server_url, token):
    """
    Establish connection to Jira using Personal Access Token
    """
    # host = "https://jira.worldline-solutions.com/"
    # token = 'VOID'  # Replace with your actual Personal Access Token

    # Set up headers with Bearer token authentication
    headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
    headers["Authorization"] = f"Bearer {token}"

    try:
        # Create Jira connection
        jira = JIRA(server=server_url, options={"headers": headers})
        print("✅ Successfully connected to Jira")
        return jira, None
    except Exception as e:
        print(f"❌ Failed to connect to Jira: {e}")
        return None, error_msg
        sys.exit(1)


def execute_jql_non_chunked(jira, jql_query):
    """
    Execute JQL query in chunks to avoid overloading Jira
    """
    print("✅ Running Jira query for all elements")

    while True:
        try:
            print(f"🔍 Fetching issues ")

            # Fetch all issues
            issues = jira.search_issues(jql_query, maxResults=10000)

            if not issues:
                break

            all_issues.extend(issues)

        except Exception as e:
            raise Exception(f"Error fetching issues at offset {start_at}: {str(e)}")

    print(f"📊 Total issues fetched: {len(all_issues)}")

    return all_issues


def execute_jql_chunked(jira, jql_query):
    """
    Execute JQL query in chunks to avoid overloading Jira
    """
    all_issues = []
    start_at = 0
    print(f"✅ Running Jira query for {chunk_size} elements")

    while True:
        flash(f"🔍 Fetching issues {start_at} to {start_at + chunk_size}")
        try:
            print(f"🔍 Fetching issues {start_at} to {start_at + chunk_size}")
            # update the interface
            flash(
                "🔍 Fetching issues... please wait till the redirection... ", "warning"
            )

            # Fetch chunk of issues
            issues = jira.search_issues(
                jql_query,
                startAt=start_at,
                maxResults=chunk_size,
                expand="changelog",  # Include changelog for additional data if needed
            )

            if not issues:
                break

            print(f"🔍 Issues len {len(issues)}")

            all_issues.extend(issues)

            # If we got fewer issues than chunk_size, we've reached the end
            if len(issues) < chunk_size:
                break

            start_at += chunk_size

        except Exception as e:
            raise Exception(f"Error fetching issues at offset {start_at}: {str(e)}")

    print(f"📊 Total issues fetched: {len(all_issues)}")

    return all_issues


# clean HTML from text
def clean_html_content_with_bs4(text):
    """
    Clean HTML content using BeautifulSoup (requires: pip install beautifulsoup4)
    """
    if not text:
        return ""

    try:
        # Parse HTML
        soup = BeautifulSoup(text, "html.parser")

        # Get text content
        clean_text = soup.get_text(separator=" ")

        # Clean up whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        clean_text = clean_text.strip()
        print(f"📊 Text cleand before: {clean_text}")
        
        clean_text = clean_html_content (clean_text)
        
        #print(f"📊 Text cleand after additional: {clean_text}")
        
        return clean_text

    except Exception as e:
        # Fallback to regex method
        return str(text)


# new file creator
def save_issues_to_csv_file(issues, filename):
    """
    Save Jira issues directly to a CSV file
    """
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        headers = [
            "Key",
            "Summary",
            "Issue Type",
            "Status",
            "Priority",
            "Assignee",
            "Reporter",
            "Created",
            "Updated",
            "Resolution",
            "Components",
            "Labels",
            "Description",
            "Parent Link",
        ]
        writer.writerow(headers)

        # Write issue data
        for issue in issues:
            try:
                # Handle fields that might be None
                assignee = (
                    issue.fields.assignee.displayName if issue.fields.assignee else ""
                )
                reporter = (
                    issue.fields.reporter.displayName if issue.fields.reporter else ""
                )
                priority = issue.fields.priority.name if issue.fields.priority else ""
                resolution = (
                    issue.fields.resolution.name if issue.fields.resolution else ""
                )

                # Handle components (list)
                components = (
                    ", ".join([comp.name for comp in issue.fields.components])
                    if issue.fields.components
                    else ""
                )

                # Handle labels (list)
                labels = ", ".join(issue.fields.labels) if issue.fields.labels else ""

                # Handle description (might be long)
                description = ""
                if issue.fields.description:
                    try:
                        # Handle different description formats
                        if isinstance(issue.fields.description, str):
                            # Simple string description
                            description = issue.fields.description
                        elif hasattr(issue.fields.description, "content"):
                            # Atlassian Document Format (ADF) - extract text content
                            description = extract_text_from_adf(
                                issue.fields.description
                            )
                        else:
                            # Try to convert to string
                            description = str(issue.fields.description)

                        # Truncate if too long
                        if description and len(description) > 500:
                            description = description[:500] + "..."
                            description = clean_html_content(description)
                    except Exception as e:
                        description = f"[Error extracting description: {str(e)}]"
                
                # Cleaninig Description
                description_cl = clean_html_content_with_bs4 (description)
                print(f"🗑️ Cleaned description: {description_cl}")
                
                # Handle parent link (for sub-tasks, stories under epics, etc.)
                parent_link = ""
                try:
                    if hasattr(issue.fields, "parent") and issue.fields.parent:
                        parent_link = issue.fields.parent.key
                    elif (
                        hasattr(issue.fields, "customfield_10014")
                        and issue.fields.customfield_10014
                    ):  # Epic Link
                        parent_link = issue.fields.customfield_10014
                except:
                    pass  # Ignore if parent link fields don't exist

                row = [
                    issue.key,
                    issue.fields.summary,
                    issue.fields.issuetype.name,
                    issue.fields.status.name,
                    priority,
                    assignee,
                    reporter,
                    issue.fields.created,
                    issue.fields.updated,
                    resolution,
                    components,
                    labels,
                    description_cl, #cleaned
                    parent_link,
                ]
                writer.writerow(row)

            except Exception as e:
                print(f"⚠️ Error processing issue {issue.key}: {e}")
                # Write a row with just the key and error
                writer.writerow(
                    [
                        issue.key,
                        f"Error processing: {e}",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )

    """
    Convert Jira issues to CSV format
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    headers = [
        "Key",
        "Summary",
        "Issue Type",
        "Status",
        "Priority",
        "Assignee",
        "Reporter",
        "Created",
        "Updated",
        "Resolution",
        "Components",
        "Labels",
        "Description",
    ]
    writer.writerow(headers)

    # Write issue data
    for issue in issues:
        try:
            # Handle fields that might be None
            assignee = (
                issue.fields.assignee.displayName if issue.fields.assignee else ""
            )
            reporter = (
                issue.fields.reporter.displayName if issue.fields.reporter else ""
            )
            priority = issue.fields.priority.name if issue.fields.priority else ""
            resolution = issue.fields.resolution.name if issue.fields.resolution else ""

            # Handle components (list)
            components = (
                ", ".join([comp.name for comp in issue.fields.components])
                if issue.fields.components
                else ""
            )

            # Handle labels (list)
            labels = ", ".join(issue.fields.labels) if issue.fields.labels else ""

            # Handle description (might be long)
            description = (
                (issue.fields.description[:500] + "...")
                if issue.fields.description and len(issue.fields.description) > 500
                else (issue.fields.description or "")
            )

            # cleaning from html 1st
            
            description_cl = clean_html_content_with_bs4(description)
            # cleaning from html 2nd
            description = clean_html_content(description_cl)

            row = [
                issue.key,
                issue.fields.summary,
                issue.fields.issuetype.name,
                issue.fields.status.name,
                priority,
                assignee,
                reporter,
                issue.fields.created,
                issue.fields.updated,
                resolution,
                components,
                labels,
                description,
            ]
            writer.writerow(row)

        except Exception as e:
            print(f"Error processing issue {issue.key}: {e}")
            # Write a row with just the key and error
            writer.writerow(
                [
                    issue.key,
                    f"Error processing: {e}",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

    output.seek(0)
    return output.getvalue()


# Clean HTML text
def clean_html_content(text):
    """
    Clean HTML content using BeautifulSoup - Enhanced version
    """
    if not text:
        return ""

    try:
        # Convert to string if it's not already
        text = str(text)

        # First, decode HTML entities
        text = html.unescape(text)

        # Check if there's actually HTML content
        if "<" not in text and ">" not in text:
            return text.strip()

        print(f"🧹 Cleaning HTML content: {text[:100]}...")

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")

        # Replace common elements with text equivalents
        for br in soup.find_all("br"):
            br.replace_with("\n")

        for p in soup.find_all("p"):
            p.append("\n")

        for div in soup.find_all("div"):
            div.append("\n")

        for li in soup.find_all("li"):
            li.insert(0, "• ")
            li.append("\n")

        # Get clean text
        clean_text = soup.get_text(separator=" ")

        # Clean up whitespace
        clean_text = re.sub(
            r"\n\s*\n+", "\n", clean_text
        )  # Multiple newlines to single
        clean_text = re.sub(r" +", " ", clean_text)  # Multiple spaces to single
        clean_text = clean_text.strip()

        print(f"✅ Cleaned result: {clean_text[:100]}...")

        return clean_text

    except Exception as e:
        print(f"❌ BeautifulSoup cleaning failed: {e}")
        # More aggressive fallback
        try:
            # Remove all HTML tags
            clean_text = re.sub(r"<[^>]*>", "", str(text))
            # Decode HTML entities
            clean_text = html.unescape(clean_text)
            # Clean whitespace
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            print(f"🔧 Fallback cleaning result: {clean_text[:100]}...")
            return clean_text
        except:
            return str(text)


# Manage Jira format
def extract_text_from_adf(adf_content):
    """
    Extract plain text from Atlassian Document Format (ADF)
    """

    def extract_text_recursive(node):
        text = ""

        if isinstance(node, dict):
            # Handle text nodes
            if node.get("type") == "text" and "text" in node:
                text += node["text"]

            # Handle other content types
            elif "content" in node:
                for child in node["content"]:
                    text += extract_text_recursive(child)

            # Add space for paragraph breaks
            if node.get("type") == "paragraph":
                text += " "

        elif isinstance(node, list):
            for item in node:
                text += extract_text_recursive(item)

        return text

    try:
        if hasattr(adf_content, "content"):
            # If it's an object with content attribute
            return extract_text_recursive(adf_content.content).strip()
        elif isinstance(adf_content, dict):
            # If it's already a dictionary
            return extract_text_recursive(adf_content).strip()
        elif isinstance(adf_content, str):
            # If it's already a string
            return adf_content.strip()
        else:
            # Try to convert to string
            return str(adf_content).strip()
    except Exception as e:
        return f"[Could not extract description: {str(e)}]"


@app.route("/")
def index():
    return render_template("index_csv.html")


@app.route("/export", methods=["POST"])
def export_csv():
    try:
        print("✅ Successfully collected data")
        # Get form data
        server_url = request.form.get("server_url", "").strip()
        print(f"🔍 Server URL: {server_url}")
        # email = request.form.get('email', '').strip()
        # print(f"🔍 User: {email}")
        token = request.form.get("token", "").strip()
        # print(f"🔍 token: {token}")
        jql_query = request.form.get("jql_query", "").strip()
        print(f"🔍 Query: {jql_query}")

        # Validate inputs
        if not all([server_url, token, jql_query]):
            flash("All fields are required!", "error")
            return redirect(url_for("index"))

        # Ensure server URL has protocol
        if not server_url.startswith(("http://", "https://")):
            server_url = "https://" + server_url

        # Connect to Jira
        jira, error = connect_to_jira(server_url, token)
        if error:
            print(f"❌ Error: {error}")
            flash(f"Failed to connect to Jira: {error}", "error")
            return redirect(url_for("index"))

        # Execute JQL query in chunks
        print(f"🔍 Query: {jql_query}")

        # Original not working
        issues = execute_jql_chunked(jira, jql_query)
        # issues = execute_jql_non_chunked(jira, jql_query)

        if not issues:
            flash("No issues found for the given JQL query.", "warning")
            return redirect(url_for("index"))

        # Convert to CSV
        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jira_export_{timestamp}.csv"

        # Create temporary file path
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        temp_file_path = os.path.join(temp_dir, f"jira_export_{file_id}.csv")

        # Save issues directly to file
        print("📝 Saving issues to CSV file...")
        save_issues_to_csv_file(issues, temp_file_path)

        # Store file info in memory (not in session)
        with temp_files_lock:
            temp_files[file_id] = {
                "path": temp_file_path,
                "filename": filename,
                "created": datetime.now(),
                "total_issues": len(issues),
            }

        # Store only the file ID in session
        session["file_id"] = file_id

        print(f"✅ Export completed successfully! {len(issues)} issues exported.")

        # Clean up old files
        cleanup_old_files()

        return render_template(
            "result.html", total_issues=len(issues), filename=filename
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/download")
def download_csv():
    try:
        file_id = session.get("file_id")

        if not file_id:
            flash("No export data available. Please run a query first.", "error")
            return redirect(url_for("index"))

        with temp_files_lock:
            file_info = temp_files.get(file_id)

        if not file_info or not os.path.exists(file_info["path"]):
            flash(
                "Export file has expired or been deleted. Please run the query again.",
                "error",
            )
            return redirect(url_for("index"))

        filename = file_info["filename"]
        file_path = file_info["path"]

        print(f"📥 Downloading file: {filename}")

        def remove_file():
            """Remove temporary file after download"""
            time.sleep(2)  # Wait a bit to ensure download completes
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                with temp_files_lock:
                    if file_id in temp_files:
                        del temp_files[file_id]
                print(f"🗑️ Cleaned up temporary file: {filename}")
            except:
                pass

        # Schedule file cleanup after download
        threading.Thread(target=remove_file, daemon=True).start()

        return send_file(
            file_path, mimetype="text/csv", as_attachment=True, download_name=filename
        )

    except Exception as e:
        error_msg = f"Error downloading file: {str(e)}"
        print(f"❌ {error_msg}")
        flash(error_msg, "error")
        return redirect(url_for("index"))


if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Start cleanup thread
    def periodic_cleanup():
        while True:
            time.sleep(3600)  # Clean up every hour
            cleanup_old_files()

    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()

    print("🚀 Starting Jira CSV Exporter")
    print("📝 Access the application at: http://localhost:5000")
    print("🗑️ Temporary files will be cleaned up automatically")
    print("=" * 50)
    app.run(debug=True, port=5000)
