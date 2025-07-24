# jira-to-csv
<h1>This is my Python vibe coding 2nd phase</h1>

This is a web app you can run with python and enable you to connect with your Jira server and retrieve a big amount of items chunking them in 200 elements.
Than a CSV is created and you can download it.
Benefits of this solution:
✅ No Session Size Limits: Files stored on disk, not in cookies
✅ Better Performance: No memory bloat from large CSV data
✅ Automatic Cleanup: Old files are automatically removed
✅ Thread Safety: Multiple users can use the app simultaneously
✅ Scalable: Can handle very large CSV exports

<h2>Improvements</h2>
<li>Add Chunk size configurable parameter</li>
<li>Create installation package</li>

<h2>Instructions</h2>
To make this flask app working you need to do some work on your machine.

This are the package needed
- pip install pyinstaller flask jira

This is requested to enable html removal from Jira Fields
- pip install beautifulsoup4

<h2>WORK IN PROGRESS</h2>
# Jira CSV Exporter package creator

## How to Use

1. Double-click `JiraCSVExporter.exe` to start the application
2. The application will start a web server on http://localhost:5000
3. Open your web browser and go to http://localhost:5000
4. Fill in your Jira credentials:
   - Server URL: Your Jira instance URL
   - Email: Your Jira account email
   - Token: Your API token (generate from Jira settings)
   - JQL Query: Your search query
5. Click "Export to CSV" and download the results

## Requirements
- No additional software needed
- Internet connection to access Jira

## Troubleshooting
- If port 5000 is busy, the app will show an error
- Make sure your Jira credentials are correct
- Check that your JQL query is valid
