
def update_previous_dates(page, start, end, start_end, original_end=None, as_date=False, keep_midnight=False):
    # 定义目标时区，例如 'Asia/Kuala_Lumpur'
    target_tz = pytz.timezone('Asia/Kuala_Lumpur')

    # 辅助函数：安全解析日期时间
    def safe_parse(date_value):
        if date_value is None:
            return None
        if isinstance(date_value, str):
            return parse(date_value).astimezone(target_tz)
        if isinstance(date_value, date) and not isinstance(date_value, datetime):
            return datetime.combine(date_value, datetime.min.time(), tzinfo=pytz.UTC).astimezone(target_tz)
        if isinstance(date_value, datetime):
            return date_value.astimezone(target_tz)
        return None

    # 确保 'start' 和 'end' 是时区感知的 datetime 对象
    start = safe_parse(start)
    end = safe_parse(end)
    original_end = safe_parse(original_end)

    # Handle conversion of 'start_end'
    if isinstance(start_end, dict):
        start_end = [safe_parse(start_end.get('start')), safe_parse(start_end.get('end'))]
    elif isinstance(start_end, (tuple, list)):
        start_end = [safe_parse(date) for date in start_end]
    elif isinstance(start_end, datetime):
        start_end = [start_end, start_end]
    else:
        start_end = [None, None]

    # 检查是否为单日日期情况
    is_single_date = start_end[0] is not None and start_end[1] is None

    # Function to format datetime objects
    def format_date_time(date, keep_midnight=False):
        if date is None:
            return None
        date = date.astimezone(target_tz)
        if date.time() != time(0) or keep_midnight:
            return date.isoformat()
        else:
            return date.strftime('%Y-%m-%d')

    # 确定是否保留午夜时间
    keep_start_midnight = keep_midnight or (start and start.time() != time(0, 0)) or (start and start.time() == time(0, 0) and end and end.time() != time(0, 0))
    keep_end_midnight = keep_midnight or (end and end.time() != time(0, 0)) or (end and end.time() == time(0, 0) and start and start.time() != time(0, 0))

    # 格式化日期时间
    start_str = format_date_time(start, keep_midnight=keep_start_midnight)
    end_str = format_date_time(end, keep_midnight=keep_end_midnight)

    # 初始化 properties 字典
    properties = {}

    # 更新 Previous Start 和 Previous End
    if is_single_date:
        # 如果是单日日期，使用 start_end[0] 更新 Previous Start 和 Previous End
        single_date_str = format_date_time(start_end[0], keep_midnight=keep_midnight)
        properties['Previous Start'] = {'date': {'start': single_date_str}}
        properties['Previous End'] = {'date': {'start': single_date_str}}
    else:
        # 否则使用 start 和 end 更新
        properties['Previous Start'] = {'date': {'start': start_str}}
        if end_str is not None:
            properties['Previous End'] = {'date': {'start': end_str}}

    # 检查是否需要更新 Start_end
    if 'Start_end' in page['properties']:
        properties['Start_end'] = {'date': {
            'start': format_date_time(start_end[0], keep_midnight=True),
            'end': format_date_time(start_end[1], keep_midnight=True) if start_end[1] else None
        }}

    # 更新 Notion 页面
    notion.pages.update(
        page_id=page['id'],
        properties=properties
    )


def update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight=False, keep_end_midnight=False, keep_midnight=False):
    # Check and swap start and end dates if start date is after end date
    if start is not None and end is not None and start > end:
        start, end = end, start  # Swapping the dates
    
    if prev_start is not None and prev_end is not None:
        prev_start = prev_start.strftime('%Y-%m-%d %H:%M:%S%z')
        prev_end = prev_end.strftime('%Y-%m-%d %H:%M:%S%z')

    start_end = check_list([start, end])

    if not isinstance(start_end, tuple) or len(start_end) != 2:
        start_end = (start, end)
    if start_end == (None, None):
        raise ValueError("Invalid start and end dates")

    with lock:
        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

    if start_end is not None:
        with lock:
            counts['count_alldayevent'] += 1
            result['total_pages_modified'] = calculate_total(counts)

    with lock:
        update_page(local_data.page, start, end, start_end)

    with lock:
        update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=True, single_date=True, keep_midnight=keep_midnight)
        
    if start is not None and end is not None:
        with lock:
            update_previous_dates(local_data.page, start.date(), end.date(), start_end, as_date=True)
    elif start is not None and end is None:
        with lock:
            update_previous_dates(local_data.page, start.date(), None, start_end, as_date=True)

    if start_end_value is None:
        with lock:
            result['details']['set_alldayevent_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], start_end_value, result['start_end'])

    details['prev_start'] = prev_start
    details['prev_end'] = prev_end

    # Update the start and end values in the result dictionary
    result['start'] = start
    result['end'] = end

    return result, details, start, end


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
    
            # Sub Condition 4 under MASTER CONDITION D
            # All-Days-Event
            # Start and End are having Single-Date WITH time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.
            # If 'Start' and 'End' have a Single-Date
            if not has_time(local_data.page['properties']['Start']['date']['start']) and not has_time(local_data.page['properties']['End']['date']['start']):

                # Check if Start or End are explicitly set 00:00
                if start.time() == datetime.min.time() or end.time() == datetime.min.time():

                    start_end = page['properties']['StartEnd']['date']

                    if start_end['start'] is not None:
                        start_end_start = parse(start_end['start']).replace(tzinfo=start.tzinfo)
                        start_end_end = parse(start_end['end']).replace(tzinfo=end.tzinfo) if start_end['end'] is not None else None                    

                    if start_end_start.date() != start.date() or start_end_start.date() != end.date() or start_end_end is not None and start_end_end.date() != end.date():
                        # 新增的輔助函數
                        def process_start_end(start, end, start_end_start, start_end_end, StartEnd_to_Overwrite_All):
                            if StartEnd_to_Overwrite_All is True:
                                return process_overwrite_all(start, end, start_end_start, start_end_end)
                            else:
                                return process_no_overwrite(start, end, start_end_start, start_end_end)

                        def process_overwrite_all(start, end, start_end_start, start_end_end):
                            # 移除 start_end_start 和 start_end_end 的时间部分，如果时间为 00:00
                            if start_end_start.time() == time(0, 0):
                                start_end_start = datetime.combine(start_end_start.date(), time.min)
                            if start_end_end and start_end_end.time() == time(0, 0):
                                start_end_end = datetime.combine(start_end_end.date(), time.min)

                            # 原有逻辑
                            if start_end_end is None:
                                return start_end_start, start_end_start
                            elif start_end_end and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0):
                                keep_start_midnight = start.time() == time(0, 0) and end.time() != time(0, 0)
                                keep_end_midnight = end.time() == time(0, 0) and start.time() != time(0, 0)
                                return start_end_start, start_end_end
                            elif not ((start.time() == time(0, 0) and end.time() == time(0, 0) and start.date() != end.date()) and 
                                ((start.date() == start_end_start.date() or end.date() == start_end_end.date()) and 
                                (start.date() != start_end_start.date() or end.date() != start_end_end.date())) and
                                (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0))):
                                return start_end_start, start_end_end
                            return start, end

                        def process_no_overwrite(start, end, start_end_start, start_end_end):
                            # 如果 Start 和 End 都被修改，以它們為準
                            if start != prev_start or end != prev_end:
                                return start, end
                            # 檢查是否為全天事件且日期相同，如果是，則不進行任何處理
                            if start.date() == end.date() == start_end_start.date() and start.time() == end.time() == time(0, 0):
                                if start_end_end is None or start_end_start.date() == start_end_end.date():
                                    return start, end  # 直接返回原始的 start 和 end，不進行更新
                            if not (start.date() == end.date() == start_end_start.date() and start.time() == end.time() == start_end_start.time() == time(0, 0)):
                                if start_end_end is None and start_end_start.time() == time(0, 0):
                                    return start, end
                                if start != end and start_end_start == start_end_end and start.date() != start_end_start.date() and end.date() != start_end_end.date():
                                    return start, end
                                if start_end_end and start.time() == time(0, 0) and end.time() == time(0, 0) and \
                                    (start.date() != start_end_start.date() or end.date() != start_end_end.date() or start.time() != start_end_start.time() or end.time() != start_end_end.time()):
                                    return start, end
                                if (start.time() == time(0, 0) and end.time() == time(0, 0) and (start == end)) and \
                                    (start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0)) and \
                                    (start.date() != start_end_start.date() or end.date() != start_end_end.date()):
                                    return start, end
                                if start_end_end and start.date() == start_end_start.date() and end.date() == start_end_end.date() and \
                                    start_end_start != start_end_end and (start.time() == time(0, 0) and end.time() == time(0, 0)) and \
                                    (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0)):
                                    return start, end
                            return start_end_start, start_end_end


                        # 使用新的處理函數
                        new_start, new_end = process_start_end(start, end, start_end_start, start_end_end, StartEnd_to_Overwrite_All)

                        # 如果有變更，更新數據
                        if new_start != start or new_end != end:
                            start, end = new_start, new_end
                            result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value,  new_end_value, counts, start_end_value, details, keep_midnight=True)
                            pages_modified['sub_condition_4'].add(page['id'])
                            print(f"Page `{page_title}` has been modified at Sub-Condition 4 under MASTER CONDITION D\n")
        