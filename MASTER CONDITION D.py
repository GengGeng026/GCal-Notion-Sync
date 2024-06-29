
def process_pages_condition_A(page, counts, details, lock, processed_pages, return_values):

    # Initialize your result dictionary
    result = {
        'counts': {
            'count_default_time_range': 0,
            'count_auto_default_setting': 0,
            'count_alternate_alldayevent_start': 0,
            'count_alldayevent': 0,
            'count_pages_filled': 0,
            'count_pages_single_dates': 0,
            'count_pages_overwritten': 0,
            # Add more counts here as needed
        },
        'details':{
            'set_Default_details': {},
            'auto_default_setting_details': {},
            'set_Alternate_alldayevent_start_details': {},
            'set_alldayevent_details': {},
            'pages_filled_details': {},
            'pages_overwritten_details': {},
            'pages_single_dates_details': {},
        },
        'page_id': None,
        'page_title': None,
        'original_start': None,
        'original_end': None,
        'start': None,
        'end': None,
        'start_end': None,
        'prev_start': None,
        'prev_end': None,
        'prev_start_value': None,
        'prev_end_value': None,
        'new_start_value': None,
        'new_end_value': None,
        'total_pages_modified': 0
    }
    
    # Each thread will have its own 'page' dictionary
    local_data.page = dict(page)  # Create a new 'page' dictionary for each iteration
    
    # Retrieve the page id
    page_id = local_data.page['id']
    result['page_id'] = page_id  # Add this line
    
    with lock:
        if page_id in processed_pages:
            # If the page has already been processed, skip it
            return result, processed_pages
        else:
            # If the page has not been processed, add it to the set of processed pages
            processed_pages.add(page_id)

    with no_pages_operated_B_lock:
        global no_pages_operated_B
    
    # Retrieve the page id
    page_id = local_data.page['id']

    # Add the page_id to the result dictionary
    result['page_id'] = page_id
    
    # Retrieve the previous start and end properties
    prev_start, _ = get_date_from_page(local_data.page, 'Previous Start')

    prev_end, _ = get_date_from_page(local_data.page, 'Previous End')

    # Retrieve the page title
    page_title = local_data.page['properties']['Task Name']['title'][0]['text']['content']

    # Retrieve the 'Need GCal Update' property
    try:
        StartEnd_to_Overwrite_All = local_data.page['properties'][StartEnd_to_Overwrite_All_Notion_Name]['formula']['boolean']
    except KeyError:
        print(f"The property {StartEnd_to_Overwrite_All_Notion_Name} does not exist or is not a boolean formula.")
        StartEnd_to_Overwrite_All = None

    # Reset the 'start', 'end', and 'start_end' fields of the 'page' dictionary
    local_data.page['start'] = None
    local_data.page['end'] = None
    local_data.page['start_end'] = None

    # Initialize original_start and original_end
    original_start, original_end = None, None

    # Initialize 'start_end_value' at the start of the loop
    start_end_value = None

    # Initialize prev_start_value, prev_end_value, new_start_value, and new_end_value
    prev_start_value = None
    prev_end_value = None
    new_start_value = None
    new_end_value = None

    # Retrieve the start, end, and start_end properties
    start, _ = get_date_from_page(local_data.page, 'Start')
    end, _ = get_date_from_page(local_data.page, 'End')
    start_end, _ = get_date_from_page(local_data.page, 'StartEnd')


    # Convert 'start' and 'end' values to Kuala Lumpur timezone
    if isinstance(start, datetime):
        start = start.astimezone(pytz.timezone('Asia/Kuala_Lumpur'))
        # Update 'start' value in the page dictionary
        local_data.page['start'] = start.isoformat()

    if isinstance(end, datetime):
        end = end.astimezone(pytz.timezone('Asia/Kuala_Lumpur'))
        # Update 'end' value in the page dictionary
        local_data.page['end'] = end.isoformat()
    
    # Use a re-entrant lock
    lock = threading.RLock()


    # MASTER CONDITION D :  ‘Start’, End’ and ‘StarEnd’ Date Property are ALL PRESENT
    # OVERWRITE
    elif start_end is not None and start is not None and end is not None:


        # Initialize a dictionary to keep track of the pages modified by each sub-condition
        pages_modified = {
            'sub_condition_1': set(),
            'sub_condition_2': set(),
            'sub_condition_3': set(),
            'sub_condition_4': set(),
        }


        # Sub-Condition 1 under MASTER CONDITION D
        # Overwrite StartEnd accordingly 'Start' and 'End' existing dates and times
        # If 'Start' and 'End' have a Single-Date WITH a time component
        if has_time(local_data.page['properties']['Start']['date']['start']) and has_time(local_data.page['properties']['End']['date']['start']):

            # Check if Start or End are explicitly set 00:00
            if start.time() != datetime.min.time() or end.time() != datetime.min.time():

                # Store the original start and end values
                original_start = prev_start
                original_end = prev_end

                # Define start_value as the updated variable for start
                start_value = start

                # Define end_value as the updated variable for end
                end_value = end

                # Store the previous values of 'start' and 'end' at the beginning of the function
                prev_start_value = prev_start
                prev_end_value = prev_end

                # Check if start and end are set to 00:00 and start_end is empty
                if start.time() == dt.time(0, 0) or end.time() == dt.time(0, 0) and start_end == (None, None):
                    # Overwrite start_end with start and end by removing 00:00
                    start_end = (start.date(), end.date())
                    # Overwrite start and end by removing 00:00
                    start = start.date()
                    end = end.date()                    

                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                if start_value != prev_start_value or end_value != prev_end_value:

                    # Update 'StartEnd' as Time-Range accordingly 'Start' and 'End' existing dates and times
                    start_end_prop = (start_value, end_value)

                    # Save the current values of 'Start' and 'End'
                    prev_start = prev_start_value
                    prev_end = prev_end_value

                    # Update the 'start' and 'end' variables
                    start = start_end_prop[0]
                    end = start_end_prop[1]

                    # Update the page in the Notion database
                    with lock:
                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_prop)

                    # Update the 'Previous Start' and 'Previous End' properties
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end_prop)
                        print(f"Sub-Condition 1: Start or End is not set to 00:00")

                    # Update the page object
                    with lock:
                        update_page(local_data.page, start, end, start_end_prop)

                    # Update the 'result' dictionary
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, prev_start_value, prev_end_value)

                    # Increment the count of pages filled
                    with lock:
                        counts['count_pages_overwritten'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                    # Only add details to the list if 'StartEnd' was None before the update
                    with lock:
                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])


        # Sub-Condition 2 under MASTER CONDITION D
        # Overwrite Start or End
        # If 'Start' or 'End' have a Single-Date WITH a time component
        
        # Ensure 'start' and 'end' are datetime objects
        if not isinstance(start, datetime):
            start = pytz.timezone('Asia/Kuala_Lumpur').localize(datetime.combine(start, time()))
        if not isinstance(end, datetime):
            end = pytz.timezone('Asia/Kuala_Lumpur').localize(datetime.combine(end, time()))

        # Parse 'StartEnd' dates and ensure they are datetime objects with timezone
        start_end_prop = local_data.page['properties']['StartEnd']['date']
        if start_end_prop:
            start_end_start = parse(start_end_prop['start']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'start' in start_end_prop and start_end_prop['start'] is not None else None
            start_end_end = parse(start_end_prop['end']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'end' in start_end_prop and start_end_prop['end'] is not None else None

        if (end.time() != time(0, 0) or start.time() != time(0, 0)) or (end.time() == time(0, 0) and start.time() == time(0, 0)):
            
            sub_condition_2_modified = False

            if StartEnd_to_Overwrite_All == True:

                # Store the original values of 'start' and 'end' before they are overwritten
                original_start = start if isinstance(start, datetime) else start
                original_end = end if isinstance(end, datetime) else end

                # Update 'Start' and 'End' according to 'StartEnd' existing value
                start_end_prop = local_data.page['properties']['StartEnd']['date']
                if start_end_prop:
                    # Parse the dates from 'start_end_prop' and convert timezone
                    start_end_start = parse(start_end_prop['start']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'start' in start_end_prop and start_end_prop['start'] is not None else None
                    start_end_end = parse(start_end_prop['end']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'end' in start_end_prop and start_end_prop['end'] is not None else None
                
                # Check if 'StartEnd' is a Time-Range where start date is same or different from 'start' and end date is same or different from 'end'
                # And also check if Start and End are at midnight (but not set explicitly), and they are the same as the StartEnd date range, while only StartEnd has a time component set explicitly that differs from Start and End
                if start_end_end is not None and ((start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0)) and
                    (start.date() == start_end_start.date() or (start_end_end is not None and end.date() == start_end_end.date()))) or \
                    ((start.time() == time(0, 0) and end.time() == time(0, 0) and start.date() != end.date()) and 
                    (start.date() == start_end_start.date() and (start_end_end is not None and end.date() == start_end_end.date()) and 
                    (start_end_start.time() != start.time() or (start_end_end is not None and start_end_end.time() != end.time())))):

                    # Extract date part from 'start_end_prop' and update 'Start' and 'End' with the same date
                    start_date = start_end_start.date()
                    end_date = start_end_end.date()
                    
                    # Preserve timezone information from 'StartEnd Start' and 'StartEnd End'
                    start_tz = start_end_start.tzinfo
                    end_tz = start_end_end.tzinfo

                    # Update 'Start' and 'End' with the new date part while preserving the original time and timezone
                    start = datetime.combine(start_date, start_end_start.time(), tzinfo=start_tz)
                    end = datetime.combine(end_date, start_end_end.time(), tzinfo=end_tz)  # Update 'end' with the time from 'start_end_end'

                    # Only update 'start' and 'end' if the new values are different
                    if start != original_start:
                        start_value = start  # Define start_value as the updated variable for start

                    if end != original_end:
                        end_value = end  # Define end_value as the updated variable for end

                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                if start != original_start or end != original_end:
                    sub_condition_2_modified = True

                    # Save the current values of 'Start' and 'End'
                    prev_start = original_start
                    prev_end = original_end

                    # Update the page in the Notion database
                    with lock:
                        start_end_list = [parse(start_end_prop['start']), parse(start_end_prop['end'])]
                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_list)

                    # Update the 'Previous Start' and 'Previous End' properties
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end_prop)
                        print(f"Sub-Condition 2: If 'Start' or 'End' have a Single-Date WITH a time component")

                    # Update the page object
                    with lock:
                        update_page(local_data.page, start, end, start_end_prop)

                    # Update the 'result' dictionary
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end)

                    # Increment the count of pages filled
                    with lock:
                        counts['count_pages_overwritten'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                    # Only add details to the list if 'StartEnd' was None before the update
                    with lock:
                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])

                    pages_modified['sub_condition_2'].add(page['id'])
                    print(f"Page {page_title} has been modified")

        if not sub_condition_2_modified and page['id'] not in pages_modified['sub_condition_2']:

            # Initialize the flag
            is_modified = False

            # Sub Condition 3 under MASTER CONDITION D
            # Event Overwritten
            # Overwrite StartEnd accordingly Start and End
            # Start and End are having Single-Date WITHOUT time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.
            # If 'Start' and 'End' have a Single-Date
            start_end = page['properties']['StartEnd']['date']
            
            if StartEnd_to_Overwrite_All == False:
                
                # Convert 'start' and 'end' in start_end to datetime objects
                if start_end['start'] is not None or start_end['end'] is not None:
                    start_end_start = None
                    start_end_end = None

                    if start_end['start'] is not None:
                        start_end_start = parse(start_end['start']).replace(tzinfo=start.tzinfo)

                    if start_end['end'] is not None:
                        start_end_end = parse(start_end['end']).replace(tzinfo=end.tzinfo)

                        processed_sub_condtion_3 = True

                        #if start.time() != time(0, 0) and end.time() == time(0, 0) and start.date() == start_end_start.date() and end.date() == start_end_end.date():
                            #processed_sub_condtion_3 = False

                        if processed_sub_condtion_3:
                            # Check if start and end have time set to 00:00:00
                            if not (start.time() != datetime.min.time() and end.time() != datetime.min.time() and start_end_start.time() == datetime.min.time() and start_end_end.time() == datetime.min.time()) and \
                                not (start.date() == end.date() == start_end_start.date() and start.time() == end.time() == start_end_start.time() == time(0, 0)) and \
                                ((start.time() != datetime.min.time() and start.date() != start_end_start.date() and end.date() == start_end_end.date()) or
                                (end.time() != datetime.min.time() and end.date() != start_end_end.date() and start.date() == start_end_start.date())) and \
                                ((start_end_start is not None and start.date() == start_end_start.date() and start.time() != time(0, 0)) or
                                (start_end_end is not None and end.date() == start_end_end.date() and end.time() != time(0, 0)) or
                                ((start_end_start is not None and start.date() == start_end_start.date() and start.time() != start_end_start.time() and start.time() != time(0, 0)) or
                                (start_end_end is not None and end.date() == start_end_end.date() and end.time() != start_end_end.time() and end.time() != time(0, 0)))) and \
                                not ((start.time() != time(0, 0) and end.time() == time(0, 0) and start.time() != end.time()) or (start.time() == time(0, 0) and end.time() != time(0, 0) and start.time() != end.time())) and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and \
                                not ((start.time() != datetime.min.time() and end.time() == datetime.min.time()) or (start.time() == datetime.min.time() and end.time() != datetime.min.time())) or \
                                ((start.time() != time(0, 0) and end.time() == time(0, 0)) or (start.time() == time(0, 0) and end.time() != time(0, 0))) and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0):

                                # Define start_value as the updated variable for start
                                start_value = start

                                # Define end_value as the updated variable for end
                                end_value = end

                                # Store the previous values of 'start' and 'end' at the beginning of the function
                                prev_start_value = prev_start
                                prev_end_value = prev_end
                                
                                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                                if start_value != prev_start_value or end_value != prev_end_value:
                                    is_modified = True
                                    print(f"is_modified: {is_modified}")
                                    
                                    # Update 'StartEnd' as Time-Range accordingly 'Start' and 'End' existing dates and times
                                    start_end_prop = (start_value, end_value)

                                    # Save the current values of 'Start' and 'End'
                                    prev_start = prev_start_value
                                    prev_end = prev_end_value

                                    # Update the 'start' and 'end' variables
                                    start = start_end_prop[0]
                                    end = start_end_prop[1]

                                    # Update the page in the Notion database
                                    with lock:
                                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_prop)

                                    # Update the 'Previous Start' and 'Previous End' properties
                                    with lock:
                                        update_previous_dates(local_data.page, start, end, start_end_prop)

                                    # Update the page object
                                    with lock:
                                        update_page(local_data.page, start, end, start_end_prop)

                                    # Update the 'result' dictionary
                                    with lock:
                                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, prev_start_value, prev_end_value)


                                    # Increment the count of pages filled
                                    with lock:
                                        counts['count_pages_overwritten'] += 1
                                        result['total_pages_modified'] = calculate_total(counts)

                                    # Only add details to the list if 'StartEnd' was None before the update
                                    with lock:
                                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])


                                pages_modified['sub_condition_3'].add(page['id'])
                                print(f"Page {page_title} has been modified")
                        
                        
            
            if not sub_condition_2_modified and page['id'] not in pages_modified['sub_condition_2'] and not is_modified and page['id'] not in pages_modified['sub_condition_3']:

                # SUb-Sub Condition 4 under MASTER CONDITION D
                # All-Days-Event
                # Start and End are having Single-Date WITH time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.
                # If 'Start' and 'End' have a Single-Date
                    
                start_end = page['properties']['StartEnd']['date']

                if start_end['start'] is not None:
                    start_end_start = parse(start_end['start']).replace(tzinfo=start.tzinfo)
                    start_end_end = start_end['end']
                    if start_end_end is not None:
                        start_end_end = parse(start_end_end).replace(tzinfo=end.tzinfo)
                    else:
                        start_end_end = None

                    
                    # Sub-Condition 1
                    if StartEnd_to_Overwrite_All == True:
                        if start_end_start is not None and start is not None and end is not None:
                            print(f"Sub-Condition 4: Start and End are having Single-Date WITH time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.")
                            if start_end_end is None and start_end_start.time() == time(0, 0):
                                start = start_end_start
                                end = start_end_start
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_midnight=True)
                            elif start_end_end is not None and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and (start.time() != start_end_start.time() or end.time() != start_end_end.time()):
                                # Check if only start or end is overwritten by start_end_start or start_end_end respectively
                                keep_start_midnight = start.time() == time(0, 0) and end.time() != time(0, 0)
                                keep_end_midnight = end.time() == time(0, 0) and start.time() != time(0, 0)
                                start = start_end_start
                                end = start_end_end
                                result, details , start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight=keep_start_midnight)
                            elif not ((start.time() == time(0, 0) and end.time() == time(0, 0) and start.date() != end.date()) and 
                                ((start.date() == start_end_start.date() or end.date() == start_end_end.date()) and 
                                (start.date() != start_end_start.date() or end.date() != start_end_end.date())) and
                                (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0))) and not (start.time() != time(0, 0) and end.time() == time(0, 0) and start.date() == start_end_start.date() and end.date() == start_end_end.date()):
                                start = start_end_start
                                end = start_end_end
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                        # New sub-condition
                        elif start_end_start is not None and start_end_end is not None and start is not None and end is not None:
                            if start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and start.time() != end.time():
                                start = start_end_start
                                end = start_end_end
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)


                    # Sub-Condition 2
                    if StartEnd_to_Overwrite_All == False:
                        if start is not None and end is not None and start_end is not None:
                            if start_end_start is not None and start is not None and end is not None:                        
                                if not (start.date() == end.date() == start_end_start.date() and start.time() == end.time() == start_end_start.time() == time(0, 0)) or \
                                (start_end_end is not None and start.date() == end.date() == start_end_start.date() and start_end_end.date() != start.date()):
                                    if start_end_end is None and start_end_start.time() == time(0, 0):
                                        keep_start_midnight = False
                                        keep_end_midnight = False
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight, keep_end_midnight)
                                    # if start and end are not the same, but start_end_start and start_end_end are the same
                                    if start != end and start_end_start == start_end_end and start.date() != start_end_start.date() and end.date() != start_end_end.date():
                                        # Overwrite start_end as new time-range accordingly start and end
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight, keep_end_midnight)
                                    # start and end have a time component 00:00, start_end is having different dates and times from either start and end
                                    if start_end_end is not None and start.time() == time(0, 0) and end.time() == time(0, 0) and \
                                        (start.date() != start_end_start.date() or end.date() != start_end_end.date() or start.time() != start_end_start.time() or end.time() != start_end_end.time()) and \
                                        not (start.date() == start_end_start.date() and end.date() == start_end_end.date() and start_end_end.time() != time(0, 0)):
                                        # Overwrite start_end with start and end
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    if (start.time() == time(0, 0) and end.time() == time(0, 0) and (start == end)) and (start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0)) and (start.date() != start_end_start.date() or end.date() != start_end_end.date()):
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    if start_end_end is not None and start.date() == start_end_start.date() and end.date() == start_end_end.date() and start_end_start != start_end_end and \
                                        (start.time() == time(0, 0) and end.time() == time(0, 0)) and \
                                        (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0)):
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    
                                
                    pages_modified['sub_condition_4'].add(page['id'])
        
        return result, counts, details, processed_pages, page['id']
        

    # Update the result dictionary
    result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)
    
    # Add the result to the return_values queue
    return_values.put(result)
    
    return result, counts, details, processed_pages, page['id'], original_start