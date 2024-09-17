def parse_times(page):
    start, start_time_set = get_date_from_page(page, 'Start')
    end, end_time_set = get_date_from_page(page, 'End')
    start_end_prop = page['properties'].get('StartEnd') if page and 'properties' in page else None
    start_end = (get_date_from_page(page, 'StartEnd[0]'), get_date_from_page(page, 'StartEnd[1]')) if start_end_prop else None
    for date, time_set, property_name in [(start, start_time_set, 'Start'), (end, end_time_set, 'End')]:
        print_time_message(date, time_set, property_name, page['id'])
    return start, end, start_end

def format_date_time(date_value, keep_midnight=False, remove_midnight=False, as_date=False, target_tz=pytz.timezone('Asia/Kuala_Lumpur')):
    if date_value is None:
        return None

    # 將輸入轉換為 datetime 對象
    if isinstance(date_value, str):
        date_value = parse(date_value)
    elif isinstance(date_value, date) and not isinstance(date_value, datetime):
        date_value = datetime.combine(date_value, datetime.min.time())

    # 確保 datetime 對象是時區感知的
    if date_value.tzinfo is None:
        date_value = target_tz.localize(date_value)
    else:
        date_value = date_value.astimezone(target_tz)

    # 處理時間部分
    if date_value.time() != time(0) or (keep_midnight and not remove_midnight):
        if as_date:
            return date_value.date().isoformat()
        else:
            return date_value.isoformat()
    else:
        return date_value.date().isoformat()



def update_page_properties(notion, page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=False, single_date=False, update_all=True, keep_midnight=False, remove_start_end_midnight=False, keep_start_midnight=False, keep_end_midnight=False, StartEnd_to_Overwrite_All=False):
    # 將 start 和 end 轉換為 datetime 對象
    start = datetime.combine(start, datetime.min.time()) if isinstance(start, date) else start
    end = datetime.combine(end, datetime.min.time()) if isinstance(end, date) else end

    # 處理 start_end
    if isinstance(start_end, (list, tuple)) and len(start_end) == 2:
        start_end = [datetime.combine(d, datetime.min.time()) if isinstance(d, date) else d for d in start_end]
        if start_end[1] is None:
            start_end[1] = start_end[0]
    elif isinstance(start_end, (list, tuple)) and len(start_end) == 1 and isinstance(start_end[0], datetime):
        start_end.append(start_end[0])

    # 驗證輸入
    if not all(isinstance(d, datetime) for d in [start, end] + start_end if d is not None):
        print("Error: Invalid input types.")
        return

    # 確保 start 不晚於 end
    if end is not None and start > end:
        start, end = end, start

    # 準備更新負載
    properties_to_update = {}

    # 處理日期格式
    target_tz = pytz.timezone('Asia/Kuala_Lumpur')
    start_date = format_date_time(start, keep_midnight=keep_start_midnight, remove_midnight=remove_start_end_midnight, as_date=as_date, target_tz=target_tz)
    end_date = format_date_time(end, keep_midnight=keep_end_midnight, remove_midnight=remove_start_end_midnight, as_date=as_date, target_tz=target_tz) if end else None

    # 更新 Date_Notion_Name
    if start == end:
        properties_to_update[Date_Notion_Name] = {'date': {'start': start_date, 'end': None}}
    else:
        properties_to_update[Date_Notion_Name] = {'date': {'start': start_date, 'end': end_date}}

    # 更新 Start 和 End（如果需要）
    if update_all:
        properties_to_update[Start_Notion_Name] = {'date': {'start': start_date, 'end': None}}
        if end_date:
            properties_to_update[End_Notion_Name] = {'date': {'start': end_date, 'end': None}}

    # 更新 Notion 頁面
    notion.pages.update(page_id=page['id'], properties=properties_to_update)

def update_previous_dates(page, start, end, start_end, original_end=None, as_date=False, keep_midnight=False):
    target_tz = pytz.timezone('Asia/Kuala_Lumpur')

    # 轉換輸入為 datetime 對象
    start = format_date_time(start, keep_midnight=keep_midnight, target_tz=target_tz)
    end = format_date_time(end, keep_midnight=keep_midnight, target_tz=target_tz)
    original_end = format_date_time(original_end, keep_midnight=keep_midnight, target_tz=target_tz)

    # 處理 start_end
    if isinstance(start_end, dict):
        start_end = [format_date_time(start_end.get('start'), target_tz=target_tz),
                     format_date_time(start_end.get('end'), target_tz=target_tz)]
    elif isinstance(start_end, (tuple, list)):
        start_end = [format_date_time(date, target_tz=target_tz) for date in start_end]
    elif isinstance(start_end, (datetime, date)):
        start_end = [format_date_time(start_end, target_tz=target_tz), None]
    else:
        start_end = [None, None]

    # 檢查是否為單日日期情況
    is_single_date = start_end[0] is not None and start_end[1] is None

    # 準備更新負載
    properties = {}

    if is_single_date:
        single_date_str = format_date_time(start_end[0], keep_midnight=keep_midnight, target_tz=target_tz)
        properties['Previous Start'] = {'date': {'start': single_date_str}}
        properties['Previous End'] = {'date': {'start': single_date_str}}
    else:
        properties['Previous Start'] = {'date': {'start': start}}
        if end is not None:
            properties['Previous End'] = {'date': {'start': end}}

    # 更新 Start_end（如果需要）
    if 'Start_end' in page['properties']:
        properties['Start_end'] = {'date': {
            'start': format_date_time(start_end[0], keep_midnight=True, target_tz=target_tz),
            'end': format_date_time(start_end[1], keep_midnight=True, target_tz=target_tz) if start_end[1] else None
        }}

    # 更新 Notion 頁面
    notion.pages.update(page_id=page['id'], properties=properties)


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
    
    # MASTER CONDITION A : StartEnd is always None
    if start_end is None:
        
        if start is not None:
            start_date = local_data.page['properties'].get('Start', {}).get('date', {}).get('start')
        else:
            start_date = None
        if end is not None:
            end_date = local_data.page['properties'].get('End', {}).get('date', {}).get('start')
        else:
            end_date = None
        
        # Sub-condition 1 under MASTER CONDITION A
        # Defaulting All from None to 8:00 AM to 9:00 AM
        if start is None and end is None:

        # Sub-condition 2 under MASTER CONDITION A
        # Alternative to create All-Day-Event from Notion
        elif start is not None and end is None:

            # Store the original values of 'start' and 'end'
            original_start = start
            original_end = end

            # Check if 'Start' and 'End' have a Single-Date without a time component
            if has_time(local_data.page['properties']['Start']['date']['start']):

                if start.time() == datetime.min.time():
                    end = start = start

                    # Assuming start and end are defined somewhere else in your code
                    start_end = check_list([start, end])

                    # Ensure start_end is a tuple of two datetime objects
                    if not isinstance(start_end, tuple) or len(start_end) != 2:
                        start_end = (start, start)
                    if start_end == (None, None):
                        raise ValueError("Invalid start and end dates")
                    
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)
                        
                    if start_end is not None:
                        with lock:
                            counts['count_alternate_alldayevent_start'] += 1
                            result['total_pages_modified'] = calculate_total(counts)

                    with lock:
                        update_page(local_data.page, start, end, start_end)

                    with lock:
                        update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=True, single_date=True)

                    if start is not None and end is not None:
                        with lock:
                            update_previous_dates(local_data.page, start.date(), end.date(), start_end, as_date=True)
                    elif start is not None and end is None:
                        with lock:
                            update_previous_dates(local_data.page, start.date(), None, start_end, as_date=True)

                    if start_end_value is None:
                        with lock:
                            result['details']['set_Alternate_alldayevent_start_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], start_end_value, result['start_end'])

            else:
                original_start = copy.deepcopy(start)
                original_end = copy.deepcopy(end)
                original_start_end = copy.deepcopy(start_end)
                
                gmt8 = pytz.timezone('Asia/Kuala_Lumpur')
                start = datetime.now(gmt8)
                end = start + timedelta(hours=1)

                # Ensure start_end is a tuple of two datetime objects
                if not isinstance(start_end, tuple) or len(start_end) != 2:
                    start_end = (start, end)
                if start_end == (None, None):
                    raise ValueError("Invalid start and end dates")

                # Update 'start', 'end', and 'start_end' in the 'result' dictionary
                result = update_result(result, local_data.page, page_title, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

                # Increment the count of pages set to All-Day-Event
                if start_end is not None:
                    with lock:
                        counts['count_auto_default_setting'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                # Update the page object
                with lock:
                    update_page(local_data.page, start, end, start_end)

                # Update the page properties in the Notion database
                with lock:
                    update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end)
                
                if start is not None and end is not None:
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end)
                elif start is not None and end is None:
                    with lock:
                        update_previous_dates(local_data.page, start, None, start_end)           

                # Only add details to the list if 'StartEnd' was None before the update
                if start_end_value is None:
                    with lock:
                        result['details']['auto_default_setting_details'][result['page_id']] = (result['page_title'], start, end, start_end, original_start, original_end)
                        
            return result, counts, details, processed_pages, page['id'], original_start

        return result, counts, details, processed_pages, page['id']
        

    # Update the result dictionary
    result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)
    
    # Add the result to the return_values queue
    return_values.put(result)
    
    return result, counts, details, processed_pages, page['id'], original_start