import csv
import sys
import os
from datetime import datetime, timedelta
from jira import JIRA

# Jira instance details (keep your existing configuration)
JIRA_URL = "Your server"
#API_TOKEN = "Your Token"  # Your API token

def connect_to_jira(TOKEN):
    """
    Establish connection to Jira using Personal Access Token
    (Using your existing connection method - unchanged)
    """
    host = JIRA URL
    pat = TOKEN  # Replace with your actual Personal Access Token
    
    # Set up headers with Bearer token authentication
    headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
    headers["Authorization"] = f"Bearer {pat}"
    
    try:
        # Create Jira connection
        jira = JIRA(server=host, options={"headers": headers})
        print("✅ Successfully connected to Jira")
        return jira
    except Exception as e:
        print(f"❌ Failed to connect to Jira: {e}")
        sys.exit(1)

def get_issue_transitions(jira, issue_key):
    """
    Get issue details including changelog/transitions
    """
    try:
        print(f"🔍 Fetching transitions for {issue_key}")
        
        # Get issue with changelog expanded
        issue = jira.issue(issue_key, expand='changelog')
        
        # Extract transition history
        transitions = []
        if hasattr(issue, 'changelog') and issue.changelog:
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.field == 'status':
                        transitions.append({
                            'date': datetime.strptime(history.created.split('T')[0], '%Y-%m-%d'),
                            'from_status': item.fromString,
                            'to_status': item.toString,
                            'created': history.created
                        })
        
        return transitions
        
    except Exception as e:
        print(f"❌ Error fetching transitions for {issue_key}: {e}")
        return []

def find_status_transitions(transitions):
    """
    Find first 'In Progress' and last 'Done' transitions
    """
    first_in_progress = None
    last_done = None
    
    for transition in transitions:
        # Find first transition TO "In Progress" (case insensitive)
        if transition['to_status'] and 'progress' in transition['to_status'].lower():
            if first_in_progress is None:
                first_in_progress = transition
        
        # Find last transition TO "Done" (case insensitive)
        if transition['to_status'] and 'done' in transition['to_status'].lower():
            last_done = transition
    
    return first_in_progress, last_done

def calculate_days_difference(start_date, end_date):
    """
    Calculate difference in days between two dates
    """
    if start_date and end_date:
        return (end_date - start_date).days
    return None

def process_csv_file(input_file, output_file, TOKEN):
    """
    Process CSV file and add transition data
    """
    print(f"✅ Reading from {input_file}")
    print(f"✅ Output written to: {output_file}")
    
    # Connect to Jira
    jira = connect_to_jira(TOKEN)
    
    # Read input CSV
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            csv_reader = csv.reader(infile)
            rows = list(csv_reader)
            
        if not rows:
            print("❌ Input file is empty")
            return
            
        print(f"📁 Processing {len(rows)} rows from {input_file}")
        
        # Process each row
        output_rows = []
        header_row = rows[0] if rows else []
        
        # Add new column headers
        new_headers = header_row + [
            'First_In_Progress_Date', 
            'Last_Done_Date', 
            'Days_In_Progress_To_Done'
        ]
        output_rows.append(new_headers)
        
        # Process data rows (skip header)
        for i, row in enumerate(rows[1:], 1):
            if not row:  # Skip empty rows
                continue
                
            issue_key = row[0].strip() if row else ""
            
            if not issue_key:
                print(f"⚠️ Row {i}: Empty issue key, skipping")
                output_rows.append(row + ["", "", ""])
                continue
            
            print(f"📋 Processing {i}/{len(rows)-1}: {issue_key}")
            
            # Get transitions for this issue
            transitions = get_issue_transitions(jira, issue_key)
            print(f"📋 Transitions {transitions}")
            
            # Find relevant transitions
            first_in_progress, last_done = find_status_transitions(transitions)
            
            # Extract dates and calculate difference
            in_progress_date = ""
            done_date = ""
            days_diff = ""
            
            if first_in_progress:
                in_progress_date = first_in_progress['date'].strftime('%Y-%m-%d')
                
            if last_done:
                done_date = last_done['date'].strftime('%Y-%m-%d')
            
            if first_in_progress and last_done:
                days_diff = calculate_days_difference(
                    first_in_progress['date'], 
                    last_done['date']
                )
                days_diff = str(days_diff) if days_diff is not None else ""
            
            # Add data to output row
            output_row = row + [in_progress_date, done_date, days_diff]
            output_rows.append(output_row)
            
            print(f"   ✅ In Progress: {in_progress_date}, Done: {done_date}, Days: {days_diff}")
        
        # Write output CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            csv_writer = csv.writer(outfile)
            csv_writer.writerows(output_rows)
            
        print(f"✅ Output written to: {output_file}")
        print(f"📊 Processed {len(output_rows)-1} issues")
        
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_file}")
    except Exception as e:
        print(f"❌ Error processing file: {e}")

def main():
    """
    Main function
    """
    print("🚀 Jira Status Transition Analyzer")
    print("=" * 50)
    
    # Get input/output file paths
    if len(sys.argv) != 4:
        print("Usage: python jira_status_analyzer.py <input_csv> <output_csv> <KEY>")
        print("Example: python jira_status_analyzer.py issues.csv issues_with_transitions.csv APIKEYSSSSS")
        
        # Interactive mode if no arguments provided
        input_file = input("Enter input CSV file path: ").strip()
        output_file = input("Enter output CSV file path: ").strip()
        TOKEN = input("Enter your private API_TOKEN: ").strip()

    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        TOKEN = sys.argv[3]
    
    # Validate input file exists
    if not os.path.exists(input_file):
        print(f"❌ Input file does not exist: {input_file}")
        return
    
    print(f"📥 Input file: {input_file}")
    print(f"📤 Output file: {output_file}")
    print(f"📤 Key: {TOKEN}")
    
    # Process the file
    process_csv_file(input_file, output_file,TOKEN)
    
    print("\n🎉 Analysis completed!")

if __name__ == "__main__":
    main()