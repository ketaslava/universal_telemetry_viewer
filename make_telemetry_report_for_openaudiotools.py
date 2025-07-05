import os
import json
import matplotlib.pyplot as plt
from orca.debug import println
from sympy import floor


def check_required_data_structure(data):
    return ("unixTime" in data and "installationId" in
             data and data.get("appName") == "OpenAudioTools")


def load_telemetry_data():

    non_json_count = 0
    non_standard_count = 0
    files_data = []

    for filename in os.listdir(TELEMETRY_DIR):

        # Read only .txt files
        if not filename.endswith(".txt"):
            continue

        # Read only json files + count non json
        current_file_path = os.path.join(TELEMETRY_DIR, filename)
        try:
            with open(current_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            file_data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            non_json_count += 1
            continue

        # Count non-standard files and skip
        if not check_required_data_structure(file_data):
            non_standard_count += 1
            continue

        # Collect data
        files_data.append(file_data)

    return files_data, non_json_count, non_standard_count


def get_users_action_structure(data):
    # Get user actions structure as { installationId: { statement: [ unixTime ] } }
    user_actions = {}
    for frame in data:
        iid = frame.get("installationId")
        if iid not in user_actions.keys():
            user_actions[iid] = {}
    return user_actions


def add_statement_per_user(data, user_actions, statement_type, statement):
    # Count particular statements like "statementType": "sixHoursActivityReport" per user
    for frame in data:
        if statement_type in frame and frame.get(statement_type) == statement:
            iid = frame.get("installationId")
            unix_time = frame.get("unixTime")
            if statement not in user_actions[iid]:
                user_actions[iid][statement] = []
            user_actions[iid][statement].append(unix_time)
    return user_actions


def count_statements(user_actions, statement):
    # Count particular statements like "statementType": "sixHoursActivityReport" overall
    statements_count = 0
    for user in user_actions:
        if statement in user_actions[user]:
            statements_count += len(user_actions[user][statement])
    return statements_count


def count_users_with_existent_statement(user_actions, statement):
    # Count users who have at least one particular statement
    users_count = 0
    for user in user_actions:
        if statement in user_actions[user]:
            users_count += 1
    return users_count


def count_statements_per_time_frame(
        user_actions, statement, start_time, end_time, is_max_one_per_frame=False):
    # Count users who have at least one particular statement
    statements_count = 0
    for user in user_actions:
        if statement in user_actions[user]:
            dates = user_actions[user][statement]
            for date in dates:
                if start_time < int(date) < end_time:
                    statements_count += 1
                    if is_max_one_per_frame:
                        continue
    return statements_count


def calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, start_time, end_time, time_step, is_max_one_per_time_step=False):

    graph_data = []
    start_times = []

    # Check
    if end_time <= start_time:
        println("ERROR in create_graph: incorrect time")

    # Create time steps
    time = start_time
    while time < end_time:
        start_times.append(time)
        time += time_step

    # Get count for time frames
    for start in start_times:
        graph_data.append(count_statements_per_time_frame(
            user_actions, statement, start, start + time_step, is_max_one_per_time_step))

    return graph_data


def create_graph(graph_data, graph_name, custom_x_labels=None):

    # Get X labels
    x_labels = []

    if custom_x_labels is not None:
        # Assign X labels
        x_labels = custom_x_labels
    else:
        # Create X labels
        point_number = 0
        for _ in graph_data:
            point_number += 1
            x_labels.append(str(point_number))

    # Plot the graph
    plt.figure(figsize=(12, 5))
    plt.plot(x_labels, graph_data, marker='o', linestyle='-', color='teal')
    plt.title(graph_name)
    plt.xlabel("Time (UTC)")
    plt.ylabel("Number of Statements")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = os.path.join(REPORT_DIR, f"{graph_name}.png")
    plt.savefig(filename, dpi=150)
    plt.close()


def new_statistics_file():
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, STATS_FILE)
    # Open in write mode to create or clear existing file, then immediately close
    with open(path, 'w', encoding='utf-8') as f:
        pass  # truncates file


def append_statistics_line(line: str):
    path = os.path.join(REPORT_DIR, STATS_FILE)
    # Ensure the file is initialized
    os.makedirs(REPORT_DIR, exist_ok=True)
    # Append the line
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line.rstrip("\n") + "\n")


def count_popularity_of_statement_variants(data, dictionary, statement):
    if statement in data:
        variant = data.get(statement)
        if variant not in dictionary.keys():
            dictionary[variant] = 0
        dictionary[variant] += 1
    return dictionary


def sort_and_unpack_popularity_dictionary(dictionary):
    dictionary_sorted = sorted(dictionary.items(), key=lambda item: item[1], reverse=True)
    keys, values = zip(*dictionary_sorted)
    return keys, values


def display_data(data, non_json_files, non_standard_files):

    # ---- Setup ---- #

    # Cleanup
    new_statistics_file()

    # Get structure
    user_actions = get_users_action_structure(data)

    # Add statements

    # Activity
    user_actions = add_statement_per_user(data, user_actions,
                                          "statementType", "sixHoursActivityReport")

    # Installations
    user_actions = add_statement_per_user(data, user_actions,
                                          "statementType", "newInstallationLaunchReport")

    # Checkpoints
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "secondLaunch")
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingSavedFirstTime")
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingPreviewPlayedFirstTime")
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingLoadedFirstTime")

    # Functions
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingSaved")
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingPreviewPlayed")
    user_actions = add_statement_per_user(data, user_actions,
                                          "checkpointName", "recordingLoaded")

    # ---- Activity ---- #

    # Activity graph (1H)
    graph_name = "Active users per hour"
    statement = "sixHoursActivityReport"
    time_step = 3600  # 1 hour
    # Calculate graph data
    graph_data = calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, START_TIME, END_TIME, time_step, True)
    create_graph(graph_data, graph_name)

    # Activity graph (1d)
    graph_name = "Active users per day"
    statement = "sixHoursActivityReport"
    time_step = 86400  # 1 day
    graph_data = calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, START_TIME, END_TIME, time_step, True)
    create_graph(graph_data, graph_name)

    # Activity graph (1W)
    graph_name = "Active users per week"
    statement = "sixHoursActivityReport"
    time_step = 604800  # 1 week
    graph_data = calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, START_TIME, END_TIME, time_step, True)
    create_graph(graph_data, graph_name)

    # Activity graph (1M)
    graph_name = "Active users per month"
    statement = "sixHoursActivityReport"
    time_step = 2419200  # 1 month
    graph_data = calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, START_TIME, END_TIME, time_step, True)
    create_graph(graph_data, graph_name)

    # New installation launches
    graph_name = "New installation launches per day"
    statement = "newInstallationLaunchReport"
    time_step = 86400  # 1 day
    graph_data = calculate_graph_data_by_statements_count_per_time(
        user_actions, statement, START_TIME, END_TIME, time_step, True)
    create_graph(graph_data, graph_name)

    # ---- Installations, Checkpoints, Functions ---- #

    # Statistics
    append_statistics_line(f"Statistics:")

    # Not included files
    append_statistics_line(f"Non-JSON files: {non_json_files}")
    append_statistics_line(f"Non-standard JSON files: {non_standard_files}")

    # Installations
    append_statistics_line(f"")
    append_statistics_line(f"Installations:")

    # New installation launch report
    count = count_users_with_existent_statement(user_actions, "newInstallationLaunchReport")
    append_statistics_line(f"New installations launch report: {count}")

    # Checkpoints
    append_statistics_line(f"")
    append_statistics_line(f"Checkpoints:")

    # Second launch
    count = count_users_with_existent_statement(user_actions, "secondLaunch")
    append_statistics_line(f"Second launch: {count}")

    # Recording saved first time
    count = count_users_with_existent_statement(user_actions, "recordingSavedFirstTime")
    append_statistics_line(f"Recording saved first time: {count}")

    # Recording preview played first time
    count = count_users_with_existent_statement(user_actions, "recordingPreviewPlayedFirstTime")
    append_statistics_line(f"Recording preview played first time: {count}")

    # Recording loaded first time
    count = count_users_with_existent_statement(user_actions, "recordingLoadedFirstTime")
    append_statistics_line(f"Recording loaded first time: {count}")

    # Functions
    append_statistics_line(f"")
    append_statistics_line(f"Functions:")

    # Recording saved
    count = count_statements(user_actions, "recordingSaved")
    append_statistics_line(f"Recording saved: {count}")

    # Recording preview played
    count = count_statements(user_actions, "recordingPreviewPlayed")
    append_statistics_line(f"Recording preview played: {count}")

    # Recording loaded
    count = count_statements(user_actions, "recordingLoaded")
    append_statistics_line(f"Recording loaded: {count}")

    # ---- User lifetime ---- #

    lifetime_duration_days = []
    graph_name = "User lifetime duration days"
    time_step_day = 86400  # 1 day

    # Calculate, how many days user lifetime lasts X: days Y: amount of users
    for user in user_actions:
        if "sixHoursActivityReport" in user_actions[user]:
            dates = user_actions[user][statement]
            lowest_time = dates[0]
            highest_time = dates[0]
            for date in dates:
                if date < lowest_time:
                    lowest_time = date
                if date > highest_time:
                    highest_time = date
            days = int(floor((int(highest_time) - int(lowest_time)) / time_step_day))
            while len(lifetime_duration_days) <= days:
                lifetime_duration_days.append(0)
            lifetime_duration_days[days] += 1

    # Create graph
    create_graph(lifetime_duration_days, graph_name)

    # ---- User Info Report ---- #

    # Variables
    platform_popularity = {}
    language_popularity = {}
    country_popularity = {}
    timezone_popularity = {}

    # Count
    for frame in data:
        if (("statementType" not in frame) or ("deviceType" not in frame) or
                (frame.get("statementType") != "newInstallationLaunchReport")):
            continue # Skip non newInstallationLaunchReport types

        # Process platforms
        platform_popularity = count_popularity_of_statement_variants(
                frame, platform_popularity, "deviceType")

        # Process by platform
        device_type = frame.get("deviceType")
        if device_type == "Desktop" or device_type == "Android":

            # Language popularity
            language_popularity = count_popularity_of_statement_variants(
                frame, language_popularity, "language")

            # Country popularity
            country_popularity = count_popularity_of_statement_variants(
                frame, country_popularity, "country")

            # Time zone popularity
            timezone_popularity = count_popularity_of_statement_variants(
                frame, timezone_popularity, "timeZone")

    # Make graphs

    keys, values = sort_and_unpack_popularity_dictionary(platform_popularity)
    create_graph(values, "Platform Popularity", keys)

    keys, values = sort_and_unpack_popularity_dictionary(language_popularity)
    create_graph(values, "Language Popularity", keys)

    keys, values = sort_and_unpack_popularity_dictionary(country_popularity)
    create_graph(values, "Country Popularity", keys)

    keys, values = sort_and_unpack_popularity_dictionary(timezone_popularity)
    create_graph(values, "Time Zone Popularity", keys)


# Config
TELEMETRY_DIR = "collected_telemetry"
REPORT_DIR = "telemetry_report_for_openaudiotools"
STATS_FILE = "statistics.txt"
# Time frame
START_TIME = 1751612400
END_TIME = 1751665363

# Process
data_rows, non_json, non_standard = load_telemetry_data()
display_data(data_rows, non_json_files=non_json, non_standard_files=non_standard)
