
def update_page_properties(notion, page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=False, single_date=False, update_all=True, keep_midnight=False, remove_start_end_midnight=False, keep_start_midnight=False, keep_end_midnight=False, StartEnd_to_Overwrite_All=False):
    # Convert 'start' and 'end' into datetime objects if they are not already
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if end is not None and isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time())

    # 在更新 start 和 end 之前，首先检查 start 是否为空，并根据 start_end 进行更新
    if start is None and end is not None:
        if isinstance(start_end, (list, tuple)) and len(start_end) == 2:
            start = start_end[0]  # 使用 start_end 的第一个元素更新 start
        else:
            print("Error: start_end does not have the expected format.")
            return

    if isinstance(start_end, (list, tuple)) and len(start_end) == 2:
        start_end = [datetime.combine(d, datetime.min.time()) if isinstance(d, date) and not isinstance(d, datetime) else d for d in start_end]
        if start_end[1] is None:
            start_end[1] = start_end[0]

    if isinstance(start_end, (list, tuple)) and len(start_end) == 1 and isinstance(start_end[0], datetime):
        start_end.append(start_end[0])

    if not isinstance(start, datetime) or (end is not None and not isinstance(end, datetime)) or not isinstance(start_end, (list, tuple)) or len(start_end) != 2 or not all(isinstance(date, datetime) for date in start_end):
        print("Error: Invalid input types.")
        return

    # Get the current timezone for Asia/Kuala Lumpur
    kuala_lumpur_tz = pytz.timezone('Asia/Kuala_Lumpur')

    # Function to adjust datetime to Kuala Lumpur timezone without adding extra hours
    def adjust_to_kl_timezone(dt, tz):
        # Check if datetime is naive or already in the target timezone
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # If naive, localize to the target timezone
            return tz.localize(dt)
        else:
            # If already timezone-aware, convert to the target timezone
            # Use normalize to correctly handle daylight saving time transitions
            return tz.normalize(dt.astimezone(tz))

    # Adjust 'start' and 'end' to Kuala Lumpur timezone
    start = adjust_to_kl_timezone(start, kuala_lumpur_tz)
    if end is not None:
        end = adjust_to_kl_timezone(end, kuala_lumpur_tz)

    # 在日期对象验证通过后，构建更新负载之前添加
    if end is not None and start > end:
        # 如果 start 晚于 end，则交换它们
        start, end = end, start
        
    # 直接准备更新负载，避免中间状态
    properties_to_update = {}

    # # 根据 single_date 参数更新逻辑
    # if single_date and start == end:
    #     end = None  # 清空 end

    # 如果 single_date 为 False，则需要检查 start 和 end 是否与 start_end 中的值相同
    if not single_date and start == start_end[0] and end == start_end[1]:
        # 如果 start 和 end 与 start_end[1] 相同，不应清空 end
        pass  # 保持 end 不变

    # Ensure start and end are not None before proceeding
    if start is not None and end is not None:
        # 检查 start 和 end 的日期是否与 StartEnd 相同，并且时间都为 00:00
        if start.date() == start_end[0].date() and end.date() == start_end[1].date() and start.time() == time(0, 0) and end.time() == time(0, 0):
            # 移除 00:00 时间
            start_date = format_date_time(start, keep_midnight=False, remove_midnight=True)
            end_date = format_date_time(end, keep_midnight=False, remove_midnight=True)
        else:
            # 检查 start 和 end 的日期是否与 StartEnd 相同
            if start.date() == start_end[0].date() and end.date() == start_end[1].date():
                # 检查 start 或 end 是否为 00:00
                if start.time() == time(0, 0) or end.time() == time(0, 0):
                    # 如果 start 为 00:00，则在更新时保留这个时间
                    if start.time() == time(0, 0):
                        start_date = format_date_time(start, keep_midnight=True, remove_midnight=False)
                    else:
                        start_date = format_date_time(start, keep_midnight=keep_start_midnight, remove_midnight=remove_start_end_midnight)
                    
                    # 如果 end 为 00:00，则在更新时保留这个时间
                    if end.time() == time(0, 0):
                        end_date = format_date_time(end, keep_midnight=True, remove_midnight=False)
                    else:
                        end_date = format_date_time(end, keep_midnight=keep_end_midnight, remove_midnight=remove_start_end_midnight)
                else:
                    # 如果不满足特定条件，则使用原始逻辑
                    start_date = format_date_time(start, keep_midnight=keep_start_midnight, remove_midnight=remove_start_end_midnight)
                    end_date = format_date_time(end, keep_midnight=keep_end_midnight, remove_midnight=remove_start_end_midnight)
            else:
                # 如果日期不匹配
                # 检查 start 和 end 是否都为 00:00
                if start.time() == time(0, 0) and end.time() == time(0, 0):
                    # 移除 00:00 时间
                    start_date = format_date_time(start, keep_midnight=False, remove_midnight=True)
                    end_date = format_date_time(end, keep_midnight=False, remove_midnight=True)
                else:
                    # 如果不是全都 00:00，使用原始逻辑
                    start_date = format_date_time(start, keep_midnight=keep_start_midnight, remove_midnight=remove_start_end_midnight)
                    end_date = format_date_time(end, keep_midnight=keep_end_midnight, remove_midnight=remove_start_end_midnight)
    else:
        # Handle the case where start or end is None
        print("Error: start or end is None")
        return

    # # Apply midnight removal consistently if needed
    # if remove_start_end_midnight:
    #     start_date = format_date_time(start, keep_midnight=False, remove_midnight=True) if start.time() == time(0, 0) else start_date
    #     end_date = format_date_time(end, keep_midnight=False, remove_midnight=True) if end.time() == time(0, 0) else end_date
    # else:
    #     start_date = format_date_time(start, keep_midnight=keep_start_midnight)
    #     end_date = format_date_time(end, keep_midnight=keep_end_midnight)

    # 如果 start 和 end 相同，则视为单一日期
    if start == end:
        properties_to_update[Date_Notion_Name] = {
            'date': {
                'start': start_date,
                'end': None  # 或者使用 end_date，根据实际情况决定
            }
        }
    else:
        properties_to_update[Date_Notion_Name] = {
            'date': {
                'start': start_date,
                'end': end_date
            }
        }

    # 更新 Start 和 End（如果需要）
    if update_all:
        properties_to_update[Start_Notion_Name] = {
            'date': {
                'start': start_date,
                'end': None  # Start 通常不需要 end 时间
            }
        }
        if end_date is not None:
            properties_to_update[End_Notion_Name] = {
                'date': {
                    'start': end_date,  # End 可能只需要 start 时间，这里根据实际情况调整
                    'end': None
                }
            }

    # 一次性更新 Notion 页面，避免不必要的中间状态
    notion.pages.update(
        page_id=page['id'],
        properties=properties_to_update
    )



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
    
            # SUb-Sub Condition 4 under MASTER CONDITION D
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
        