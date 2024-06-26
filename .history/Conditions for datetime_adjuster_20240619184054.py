"""
Conditions for datetime_adjuster.py
------------------------------------

This module contains the conditions and functions for adjusting datetime properties within pages.

Sections:
- Section A: Filter out pages
- Section B: Sync dates to 'StartEnd'
- Section C: Overwrite 'StartEnd'
"""

"""
───────────────────────────── PREVIOUS SETTING ─────────────────────────────
"""

''' Section A '''
# Filter out each Page where 'to Auto Sync' formula property is unchecked. Keep those pages checked as result.

''' Section B '''
# When 'StartEnd' is Empty, Take 'Start' and 'End' Dates and Sync to 'StartEnd'

''' Section C '''
# When 'StartEnd' is Not Empty, Overwrite 'StartEnd' accordingly 'Start' and 'End'Ω

# Functions:
# - check_and_update_properties(page)
# - check_start_end_property(page)
# - overwrite_start_end(page)
# - overwrite_start_end_from_start_end(page)
# - overwrite_start_end_from_start_end_modified(page)

# Variables:
# - modified_pages_count
# - check_start_end_property.no_modification_count
# - check_start_end_property.no_modification_pages
# - overwrite_start_end_count
# - overwrite_start_end_from_start_end_count
# - overwrite_start_end_from_start_end_modified_count


"""
────────────────────────── 而我實際需要の順序 + 判定 ──────────────────────────
"""


''' 結構順序 '''

# 1. Filter in pages where ‘to Auto Sync’ is True only and ‘Created’ is between Last Week and Next Week of current time. 
# 2. Take ‘Start’ and ‘End’ Times not on ‘StartEnd’ and move them over to ’StartEnd’
# 3. Updating ‘StartEnd’ Times that Need to Be Updated ( Changed on Notion but need to be changed on ‘StartEnd’ )
# 4. Sync ‘StartEnd’ time updates, for times already in ’Start’ and ‘End’ back to ‘Start’ and ‘End’
# 5. Bring times ( not in ‘StartEnd’ already ) from ‘StartEnd’ to ‘Start’ and ‘End’
# 6. Deletion Sync — If marked Done in Notion, then it will delete the ‘StartEnd’ times ( and the ‘Start’ and ‘End’ once the Python API updates )

''' Section A (篩選) '''

# In this Section, all definitions are as follows:
# ‘to Auto Sync’ is formula property where either shows True or False. ‘Created’ is Single-Date Property.
# I want to create a function whereby Query each page for ‘to Auto Sync’ which is True only and ‘Created’ within current month. 

''' Section B (變量判定)''' 

In this Section, all definitions are as follows:

1. ‘Previous Start’, ‘Previous End’, ‘Start’, ‘End’, ‘StartEnd’ and ‘Last Updated Time’ Date Properties are only allowed to have Single-Date or with time included. Only ‘StartEnd’ Date Property is always allowed to have either Single-Date or Date-Range with time included. Unless there’s exception, ’StartEnd’ is ideally and supposedly always formatted in Date-Range with or without time. Otherwise, ‘StartEnd’ is considered as All-Day-Event.

Pseudocode:
def process_page(page):
    # Convert all changeable date properties to the 'Asia/Kuala_Lumpur' timezone
    for prop in ['Previous Start', 'Previous End', 'Start', 'End', 'StartEnd']:
        if prop in page:
            page[prop] = convert_to_kuala_lumpur_timezone(page[prop])

    # If 'Start' or 'End' has a date range, reset them to the default time
    if 'Start' in page and isinstance(page['Start'], list):
        page['Start'] = set_default_time_range(page)
    if 'End' in page and isinstance(page['End'], list):
        page['End'] = set_default_time_range(page)

    # If 'StartEnd' is a single date or a date range without time, consider it as an All-Day-Event
    if 'StartEnd' in page and (isinstance(page['StartEnd'], datetime) or not page['StartEnd'][0].time()):
        page['StartEnd'] = 'All-Day-Event'

    # If 'Start' and 'End' have changed, update 'Previous Start' and 'Previous End'
    if 'Start' in page and 'Previous Start' in page and page['Start'] != page['Previous Start']:
        page['Previous Start'] = page['Start']
    if 'End' in page and 'Previous End' in page and page['End'] != page['Previous End']:
        page['Previous End'] = page['End']

    return page



2. ‘Previous Start’ and ‘Previous End’ are another Date Properties where always stores ‘Start’ and ‘End’ values respectively so that it enables script to check whether ’Start’ and ‘End’ have changed or been modified.

3. Each Date Property should be updated, synchronised or overwritten in only default ‘Asia/Kuala_Lumpur’ timezone which is always GMT+8 instead of UTC.

Pseudocode:
def convert_to_kuala_lumpur_timezone(dt):
    # Convert the datetime to the 'Asia/Kuala_Lumpur' timezone
    kuala_lumpur_tz = timezone('Asia/Kuala_Lumpur')
    return dt.astimezone(kuala_lumpur_tz)


4. When mentioning `Default Setting`, it means the following conditions:
	
	a. When Date Property is Empty, Set to Default Time and Time Range:
	    
	    - If ‘Start’, ‘End’ and ‘StartEnd’ values are `None`, Start’ should be always Today 08:00, ‘End’ should be always Today 09:00 and ’StartEnd’ should be Today 08:00 to 09:00

Peudocode:
if start is None and end is None and start_end is None:
    start = default_start_time
    end = default_end_time
    start_end = (default_start_time, default_end_time)


	b. When Date Property has Single-Date with or without Time, Set to Default Time or Date Range or Time Range:
	    
	    Situation 1
	    - If only one from either ‘Start’, ‘End’ or ‘StartEnd’ has Single-Date with specific time value: 

		i. says if only ‘Start’ has Single-Date with time value ( including explicitly set 00:00 ) while ‘End’ and ‘StartEnd’ are `None`, then overwrite ‘StartEnd’ accordingly as startDate and add one more hour later than ‘Start’ to both ’StartEnd’ endDate and ‘End’.
		ii. If only ‘End’ has Single-Date with time value ( including explicitly set 00:00 ) while while ‘Start’ and ‘StartEnd’ are `None`, then overwrite ‘StartEnd’ accordingly as endDate and subtract an hour earlier than ‘End’ to both ’StartEnd’ startDate and ‘Start’.
		iii. If only ‘StartEnd’ has Single-Date with time value ( including explicitly set 00:00 ) while ‘Start’ and ‘End’ are `None`, Unless is All-Day-Event ( only has Single-Date without time value that was explicitly set 00:00 ) , then ‘StartEnd’ endDate should be always updated one more hour later than its StartDate existing time value.
	    

	    Situation 2
	    - If either ‘Start’ or ‘End’ has only Single-Date without time value ( was not explicitly set 00:00 ) while ‘StartEnd’ is `None`, both ‘Start’ and ‘StartEnd’ startDate should be always 08:00 of the existing Date, while both ‘End’ and ‘StartEnd’ endDate should be always 09:00 of the existing Date.

	    Situation 3
	    - If only ‘StartEnd’ has Single-Date without time value ( was not explicitly set 00:00 ) while 'Start' and 'End' are `None`, considered as All-Day-Event, then ‘Start’ and ‘End’ should be also overwritten accordingly the same date without time.

	   Situation 4
	    - If ‘StartEnd’ has only Date-Range with time value ( was not explicitly set 00:00 ) while 'Start' and 'End' are `None`, ‘StartEnd’ startDate should be always 08:00 and its endDate should be always 09:00.


Peudocode:
if start.date() == end.date():
        if start.time() and not end.time():
            end = start + timedelta(hours=1)
            start_end = (start, end)
        elif end.time() and not start.time():
            start = end - timedelta(hours=1)
            start_end = (start, end)
        elif start_end and not start_end[0].time() and not start_end[1].time():
            start = start_end[0].replace(hour=8, minute=0)
            end = start_end[1].replace(hour=9, minute=0)
            start_end = (start, end)



	c. When Date Property has Date Range without Time, Set to Default Single Date:
	    - If ‘StartEnd’ has only Date-Range without time value, ‘Start’ and ‘End’ should be also overwritten accordingly the same dates without time.

Peudocode:
if start.date() != end.date() and not start.time() and not end.time():
        start_end = (start, end)


AS A WHOLE:

if Start is None and End is None and StartEnd is None:
    Set Start to today at 08:00
    Set End to today at 09:00
    Update StartEnd to span from Start to End

else if Start is not None and End is None and StartEnd is None:
    if Start has a date and time and the time is 00:00:
        Treat it as an all-day event and set Start, End, and StartEnd to the same date without time
    else if Start has a date and time and the time is not 00:00:
        Update StartEnd to start at Start and end at the current time
    else if Start has a date without time:
        Set Start and StartEnd to the current date and time (according to a 'Default Setting' function)

else if End is not None and Start is None and StartEnd is None:
    if End has a date and time and the time is 00:00:
        Treat it as an all-day event and set Start, End, and StartEnd to the same date without time
    else if End has a date and time and the time is not 00:00:
        Set Start to an hour before End, and update StartEnd to start at Start and end at End
    else if End has a date without time:
        Set End to the same date with a default time of 09:00, set Start to the same date with a time of 08:00, and update StartEnd to start at Start and end at End

else if Start is not None and End is not None and StartEnd is None:
    if Start and End have a date and time and the time is not 00:00:
        Update StartEnd to match Start and End
        if Start and End have the same date and time:
            Set End to one hour later than Start
        else if Start and End have different dates or times and End is set before Start:
            Swap the values of Start and End
    else if Start and End have a date and time and the time is 00:00:
        Treat it as an all-day event and set Start, End, and StartEnd to the same date without time
    else if Start and End only have a date:
        Update StartEnd to match Start and End but without the time


Pseudocode:
if StartEnd is None:
    if Start is None and End is None:
        Start = datetime.now().replace(hour=8, minute=0)
        End = datetime.now().replace(hour=9, minute=0)
        StartEnd = (Start, End)

    elif Start is not None and End is None:
        if Start.time() == datetime.min.time():
            End = Start = Start.replace(hour=0, minute=0)
            StartEnd = (Start, End)
        elif Start.time() != datetime.min.time():
            StartEnd = (Start, datetime.now())
        else:
            # Handle the case where Start has a date without time according to a 'Default Setting' function
            pass

    elif End is not None and Start is None:
        if End.time() == datetime.min.time():
            Start = End = End.replace(hour=0, minute=0)
            StartEnd = (Start, End)
        elif End.time() != datetime.min.time():
            Start = End - timedelta(hours=1)
            StartEnd = (Start, End)
        else:
            # Handle the case where End has a date without time
            pass

    elif Start is not None and End is not None:
        if Start.time() != datetime.min.time() and End.time() != datetime.min.time():
            StartEnd = (Start, End)
            if Start == End:
                End = Start + timedelta(hours=1)
            elif Start > End:
                Start, End = End, Start
        elif Start.time() == datetime.min.time() and End.time() == datetime.min.time():
            Start = Start.replace(hour=0, minute=0)
            End = End.replace(hour=0, minute=0)
            StartEnd = (Start, End)
        else:
            # Handle the case where Start and End only have a date
            pass



I want to create functions to run from CONDITION A to CONDITION B as follows:


`CONDITION A`: where ‘StartEnd’ Date Property is always `None`

First Half

In this portion, ’GCalNeedUpdate’ is always `True`. This means when the requirements are met, ‘Start’ or / and ‘End’ Date Properties should always overwrite ‘StartEnd’ Date Property, however, ‘StartEnd’ should never overwrite ‘Start’ and ‘End’ Date Properties UNLESS there’s exception for First Half of CONDITION A.

#New Task is Created from Notion

When ‘GCalNeedUpdate’ is `True`:
	
	
	#When Start, End and StartEnd are Empty, you might want to Sync All from `None` to `Default Time Range`
	
	if ‘Start’, ‘End’ and ‘StartEnd’ are all `None`, overwrite ‘Start’ Default Time to Today 08:00 and ‘End’ Default Time to Today 09:00. After that, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. Otherwise, skip.
	Print those page(s’) ‘task_name’ which match the requirements and followed by its modified dates and times ( in standard format “MMM D, YYYY HH:mm” ).
	In the next newline, print “Number of Pages set Default Time Range: ” followed by total result of its “incremental value”. 



Python Code:

        if start_end is None:
            if start is None and end is None:
                
                # Store the original values of 'start' and 'end'
                original_start, original_end = start, end
                page = set_default_time_range(page, timezone)

                # Get the new values of 'start' and 'end'
                start = page.get('start')
                end = page.get('end')
                start_end = page.get('start_end')
                

                # Only print details if 'StartEnd' was None before the update
                if start_end is None:
                    print(f"Task: {page_title}")
                    print(f"Start: {DateTimeIntoNotionFormat(original_start)} → {DateTimeIntoNotionFormat(start)}")
                    print(f"End:  {DateTimeIntoNotionFormat(original_end)} → {DateTimeIntoNotionFormat(end)}")
                    start_end_value = check_list(page.get('start_end', [None, None]))
                    
                    # Print the number of pages set to default time range
                    print(f"Number of Pages set Default Time Range: {count_default_time_range}\n")

                # Assuming start and end are defined somewhere else in your code
                start_end = check_list([start, end])

                # Increment the count of pages set to default time range
                if start_end is not None:
                    count_default_time_range += 1
                    counts['count_default_time_range'] = count_default_time_range

                # Only add details to the list if 'StartEnd' was None before the update
                if start_end_value is None:
                    set_Default_details.append((page_title, start, end, start_end_value, start_end))
                    

                # Update the page in the Notion database
                if start <= end:
                    update_page_properties(notion, page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end)
                    update_previous_times(notion, page, start, end)
                else:
                    formatted_AFTER = "\033[1m\033[36mAFTER\033[0m"
                    print(f"Skipping page '{page['properties']['Task Name']['title'][0]['plain_text']}' because the start date is {formatted_AFTER} the end date")
            



	#If only Start is Present, Check whether has Time or Not
	
	If only ‘Start’ is Present whilst ‘End’ and ‘StartEnd’ are both `None`, add a check whether ‘Start’ has time value or not.
		
		#If Start has Single-Date with Time, Check whether is explicitly set to 00:00 or Not
		
		If only ‘Start’ has Single-Date with time value, add a check whether is ‘Start’ time explicitly set to 00:00 or not accordingly `get_date` function
			
		⚠️	#Alternative to create an All-Day-Event, without touching End
			#If Start Time is explicitly set to 00:00, overwrite All to Same Date
			
			If ‘Start’ time is explicitly set to 00:00, overwrite ‘Start’, ‘End’ and ‘StartEnd’ accordingly ‘Start’ existing date only without time. 
				
				#In this case, Time-Tracking from Notion is probably Still Running
				#If Start Time is Not explicitly set to 00:00 or Set Other Than 00:00, Update StartEnd
				
				Otherwise, if ‘Start’ time is not explicitly set to 00:00 but other than 00:00, then update ‘StartEnd’ startDate accordingly ‘Start’ existing date and time and endDate accordingly current time.
		
		#For All-Day-Event, Start Shall Not be Single-Date without 00:00 or End being None, Normally is a Mistake, Should be set `Default Time`
		#Enable Time-Tracking Mode
		#If Start has Single-Date with No Time, Set Start and StartEnd to `Default Time`
		
		If only ‘Start’ has Single-Date without time value, overwrite ‘Start’ with Today current time accordingly `Default Setting` function and update ‘StartEnd’ startDate accordingly ‘Start’ modified date and time then update ‘StartEnd’ endDate by adding one more hour than ‘Start’ modified time.
			
	#If only End is Present, Check whether has Time or Not
	
	If only ‘End’ is Present whilst ‘Start’ and ‘StartEnd’ are both `None`, add a check whether ‘End’ has time value or not.
		
		#If End has Single-Date with Time, Check whether is explicitly set to 00:00 or Not
		
		If only ‘End’ has Single-Date with time value, add a check whether is ‘End’ time explicitly set to 00:00 or not accordingly `get_date` function
			
		⚠️	#Another Alternative to create an All-Day-Event, without touching Start
			#If End Time is explicitly set to 00:00, overwrite All to Same Date
			
			If ‘End’ time is explicitly set to 00:00, overwrite ‘Start’, ‘End’ and ‘StartEnd’ accordingly ‘End’ existing date only without time. 
				
				#In this case, Normally is a mistake, Should Update Start and StartEnd
				#If End Time is Not explicitly set to 00:00 or Set Other Than 00:00, Update StartEnd
				
				Otherwise, if ‘End’ time is not explicitly set to 00:00 but other than 00:00, update ‘Start’ by subtracting an hour earlier than ‘End’ existing time, then update ‘StartEnd’ as time range accordingly ‘Start’ and ‘End’ modified dates and times.
		
		#End Shall Not be Standalone, Unless is Single-Date with 00:00, Normally is a Mistake, Should be set `Default Time`
		#If End has Single-Date with No Time, Set All to `Default Time`
		
		If only ‘End’ has Single-Date without time value ( not explicitly set 00:00 ), overwrite ‘End’ with same date and default time 9:00 then update ‘Start’ accordingly ‘End’ same date with 9:00. Lastly, update ‘StartEnd’ as time-range accordingly ‘Start’ and ‘End’ modified dates and times.
			

	#If both Start and End are Present, Check whether has Time or Not
	
	If only ‘StartEnd’ is `None` whilst both ‘Start’ and ‘End’ are not `None`, add a check whether ‘Start’ and ‘End’ has only Single-Date with or without specific time:
		
		#If Start and End have Single-Date with Time ( other than 00:00 ), Check whether Start and End have Different Dates and Times
		
		If both ‘Start’ and ‘End’ have Single-Date with time value ( not explicitly set 00:00 ), add a check whether ‘Start’ and ‘End’ existing dates and times are same or not.
			
			
			#If Start and End have Same Single-Date and Same Time, set All to Default Time respectively
			
			If both ’Start’ and ‘End’ have same SIngle-Date with same Time Value ( other than 00:00 ), overwrite ‘End’ by adding one more hour later than ‘Start’ accordingly ‘Default Setting’ function. Lastly, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. Otherwise, skip.
			
				#If Start and End have Same Single-Date but Different Times, Check whether is End Time set Before Start Time
				
				If ‘Start’ and ‘End’ have Same Single-Date but Different Times, Check whether is ‘End’ Time set before ‘Start’ Time.
					
					#Normally is a Mistake, Should be Reversed
					#If End Time is set Before Start Time, overwrite Start and End with `Default Time`
					
					If ‘End’ Time is set Before ‘Start’ time within same date, store ‘End’ existing value in another date property ’Previous Start’ and store ‘Start’ existing value in ‘Previous End’, respectively. Then, overwrite ‘Start’ accordingly ‘Previous Start’ while overwrite ‘End’ accordingly ‘Previous End’. Lastly, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. Otherwise, skip.

			#If Start and End have Different Single-Dates but Same Time  ( other than 00:00 ), Check whether End Date is set Before Start Date
			
		 	If both ’Start’ and ‘End’ have different SIngle-Dates with same Time Value ( not explicitly set 00:00 ), add a check whether ‘End’ date is set Before ‘Start’ date. Otherwise, skip.
				
				#Normally is a Mistake, Should be Reversed
				#If End Date is set Before Start Date but Same Time, overwrite Start and End with `Default Date`
				
				If ‘End’ date is set before ‘Start’ date but having same time value, store ‘End’ existing value in another date property ’Previous Start’ and store ‘Start’ existing value in ‘Previous End’, respectively. Then, overwrite ‘Start’ accordingly ‘Previous Start’ while overwrite ‘End’ accordingly ‘Previous End’. Lastly, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.

				
	#All-Day-Event or Days-Blocking is Purposely Created
	#If Start and End has Only SIngle-Date without Time ( including default 00:00 ), Sync StartEnd
	
	If both ‘Start’ and ‘End’ have only Single-Date without time value ( including default 00:00 ), overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ existing date without time.
			




			
`CONDITION B`: where ‘End’ Date Property is always `None`

First Half

In this portion, ’GCalNeedUpdate’ is always `True`. This means when the requirements are met, ‘Start’ or / and ‘End’ Date Properties should always overwrite ‘StartEnd’ Date Property, however, ‘StartEnd’ should never overwrite ‘Start’ and ‘End’ Date Properties UNLESS there’s exception for First Half of CONDITION B.

#either New Task is Created or or Existing Task is Modified from Notion

When ‘GCalNeedUpdate’ is `True`:
	
	
	#When Start, End and StartEnd are Empty, you might want to Sync All from `None` to `Default Time Range`
	
	if ‘Start’, ‘End’ and ‘StartEnd’ are all `None`, overwrite ‘Start’ Default Time to Today 08:00 and ‘End’ Default Time to Today 09:00. 
	After that, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. 
	Print those page(s’) ‘task_name’ which match the requirements and followed by its modified dates and times ( in standard format “MMM D, YYYY HH:mm” ).
	In the next newline, print “Number of Pages set Default Time Range: ” followed by total result of its “incremental value”. 
	
	#If only Start is Present, Check whether has Time or Not
	
	If ‘End’ and ‘StartEnd’ are both `None` whilst ‘Start’ is not `None`, add a check whether ‘Start’ has only Single-Date with or without specific time:
		
		#If Start has Single-Date with Time, Sync StartEnd and End from `None` to `Default Time Range`
		
		If ‘Start’ has time value, overwrite ‘StartEnd’ startDate accordingly ‘Start’ time whilst add one more hour later than ‘Start’ time to set as ‘StartEnd’ endDate and ‘End’ time.
			
			#If Start has Only Date, maybe is Mistake, Sync All from `None` to `Default Time Range`
			
			Otherwise, if ‘Start’ has only Single-Date without time value, then update ‘StartEnd’ endDate, ‘Start’ and ‘End’ accordingly `Default Setting`.
	

		
	#When Only StartEnd is present, Check whether has Single-Date or Date-Range
	
	If ‘Start’ and ‘End’ are both `None` whilst ‘StartEnd’ is not `None`, add a check whether ‘StartEnd’ has Single-Date or Date-Range:
		
		#If StartEnd has Only Single-Date, Check whether has Time or Not
		
		If ’StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has specific time value or not:
			
			#If StartEnd has Single-Date with Time, Update StartEnd Only
			
			If ‘StartEnd’ has Single-Date with time value, update ‘StartEnd’ endDate accordingly `Default Setting` by not updating or affecting ‘Start’ and ‘End’.
				
				#If StartEnd has Only Single-Date without Time, Skip
				
				Otherwise, do nothing.
		
		#If StartEnd has Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ startDate and endDate have specific time value or not:
			
			#New Task is Scheduled Purposedly for Time-Blocking from GCal
			
			Following sub-condition is the exception for First Half of `CONDITION B` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
				
				#If StartEnd has Date-Range with Time, Overwrite Start and End
			
				If ‘StartEnd’ has Date-Range with time values, overwrite both ‘Start’ and ‘End’ accordingly ‘StartEnd’ Time-Range. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#All-Day-Event is Purposely Scheduled
					#If StartEnd has Date-Range without Time, Overwrite Start and End
					
					Otherwise, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ Date-Range without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
	
	
	
	#In this case, Time-Tracking from Notion is probably Still Running
	#Start Shall Be Standalone without End, is Normal
	#If Start and StartEnd are Present, Check whether StartEnd has Single-Date or Date-Range

	If only ‘End’ is `None` whilst both ‘Start’ and ‘StartEnd’ are not `None`, add a check whether ‘StartEnd’ has only Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ‘StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Single-Date with Time, Check whether is Same with End or Not
			
			If ‘StartEnd’ has Single-Date with time value, add a check whether ‘Start’ is same with ‘StartEnd’ date and time:
				
		⚠️ #In this Case, StartEnd Shall be Single-Date with Time, REGARDLESS Default Duration or Time-Range
				#If StartEnd and Start are Same, Update nothing
				
				⚠️ If both ‘Start’ and ‘StartEnd’ have same Single-date and time, just leave ‘End’ empty.
					
					#In Case Start is Modified, StartEnd Should be Synchronised Accordingly
					#If StartEnd and Start are Not Same, Overwrite StartEnd
					
					Otherwise, update ‘StartEnd’ startDate accordingly ‘Start’ date and time.
			
			#If StartEnd has only Single-Date without Time, Check whether is Same with Start or Not
								
			If ‘StartEnd’ has only Single-Date without time value, add a check whether ‘Start’ is same with ‘StartEnd’:
				
				#All-Day-Event is Purposely Scheduled, Should be Synchronised
				#If StartEnd and Start are Same, Update End
				
				If both ‘Start’ and ‘StartEnd’ have only same Single-Date without time, update ‘End’ accordingly same date without time.
					
					#All-Day-Event is Purposely Scheduled, Should be Synchronised
					#If StartEnd and Start are Not Same, Overwrite StartEnd and End
					
					Otherwise,If both ‘Start’ and ‘StartEnd’ do not have same Single-Date, overwrite ‘StartEnd’ and ‘End’ accordingly ‘Start’ date.
					
					
		#If StartEnd has Complete Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Date-Range with Time, Check whether is Same with Start or Not 
			
			If ‘StartEnd’ has Date-Range with time value, add a check whether ‘Start’ is same with ‘StartEnd’ date and time:
				
				#Time-Tracking from Notion is Still Running, Don’t Overwrite End
				#If StartEnd and Start are Same, Skip
				
				If ‘Start’ is same with ‘StartEnd’ startTime, do nothing.
					
					#Time-Tracking from Notion is Still Running, Don’t Overwrite End
					#If StartEnd and Start are Not Same, Check whether Start has Time or Not

					If ‘Start’ is not same with ’StartEnd’, add a check whether ‘Start’ has time value or not,
						
						#If Start has Time, Overwrite StartEnd
						
						If ‘Start’ has time value, overwrite ‘StartEnd’ startDate only accordingly ‘Start’ date and time.
							
							Following sub-condition is the exception for First Half of `CONDITION B` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
								
								#Start Should has Time, Otherwise is a Mistake
								#If Start has Single-Date without Time, Overwrite Start
								
								If ‘Start’ has only Single-Date without time value, overwrite ‘Start’ accordingly ‘StartEnd’ startDate and time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
			
			#If StartEnd has only Date-Range without Time, Check whether is Same with Start or Not
			
			If ‘StartEnd’ has only Date-Range without time value, add a check whether ‘Start’ is same with ‘StartEnd’:
				
				Following sub-condition is the exception for First Half of `CONDITION B` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
					
					#Days-Blocking is Purposely Scheduled, Should be Synchronised
					#If StartEnd and Start are Same, Update End
					
					If ‘Start’ is same with ‘StartEnd’ startDate without time, overwrite ‘End’ accordingly ‘StartEnd’ endDate.
						
						#If StartEnd and Start are Not Same, Check whether Start has Time or Not
						
						If ‘Start’ is not same with ’StartEnd’, add a check whether ‘Start’ has time value or not,
						
							#If Start has Single-Date with Time, Overwrite StartEnd
							
							If ‘Start’ has Single-Date with time value, overwrite ‘StartEnd’ startDate only accordingly ‘Start’ date and time.
								
								#If Start has Single-Date without Time, is a Mistake, Overwrite StartEnd
								
								Otherwise, If ‘Start’ has Single-Date without time value, overwrite ‘Start’ accordingly ‘StartEnd’ startDate. After that, overwrite ‘Last Updated Time’ accordingly current time.


Second Half

In this portion,‘GCalNeedUpdate’ is always `False`. This means when the requirements are met, ‘StartEnd’ Date Property should always overwrite ‘Start’ or / and ‘End’ Date Properties, however, ‘Start’ or / and ‘End’ Date Properties should never overwrite ‘StartEnd’ Date Property UNLESS there’s exception for Second Half of CONDITION B.

#either New Task is Created or Existing Task is Modified from GCal

When ‘GCalNeedUpdate’ is `False`:



	#When Start, End and StartEnd are Empty, You Might Want to Sync All from `None` to `Default Time Range`
	
	if ‘Start’, ‘End’ and ‘StartEnd’ are all `None`, overwrite ‘StartEnd’ default time to Today 08:00 and 09:00. 
	After that, update ‘Start’ and ‘End’ accordingly ‘StartEnd’ modified dates and times.
	Print those page(s’) ‘task_name’ which match the requirements and followed by modified dates and times ( in standard format “MMM D, YYYY HH:mm” ).
	In the next newline, print “Number of Pages set Default Time Range: ” followed by total result of its “incremental value”. 
	
	
	#When only StartEnd is Present, Check whether has Single-Date or Date-Range
	
	If ‘Start’ and ‘End’ are both `None` whilst ‘StartEnd’ is not `None`, add a check whether ‘StartEnd’ has Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ’StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has specific time value or not:
			
			#If StartEnd has Single-Date with Time, maybe is Mistake, Update StartEnd, Start and End 
			
			If  ‘StartEnd’ has Single-Date with time value, update ‘StartEnd’ endDate accordingly `Default Setting` and overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ modified date and time.
				
				#All-Day-Event is Purposely Scheduled from GCal
				#If StartEnd has Only Single-Date without Time, Overwrite Start and End
				
				Otherwise, If ‘StartEnd’ has Single-Date without time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ same date. After that, overwrite ‘Last Updated Time’ accordingly current time.
		
		#If StartEnd had Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ startDate and endDate have specific time value or not:
			
			#New Task is Created for Detailed Time-Blocking from GCal
			#If StartEnd has Date-Range with Time, Skip
			
			If ‘StartEnd’ has Date-Range with time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing dates and times. After that, overwrite ‘Last Updated Time’ accordingly current time.
				
				#New Task is Created for Days-Blocking from GCal
				#If StartEnd has Only Date-Range without Time, Update StartEnd, Start and End to `Default Time`
				
				Otherwise, If ‘StartEnd’ has Date-Range without time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing dates only without time. After that, overwrite ‘Last Updated Time’ accordingly current time.

	
	
	#In this case, Event is modified from Cal while Time-Tracking from Notion is probably Still Running
	#Start Shall Be Standalone without End, is Normal
	#If End and StartEnd are Present, Check whether StartEnd has Single-Date or Date-Range

	If only ‘End’ is `None` whilst both’ Start’ and ‘StartEnd’ are not `None`, add a check whether ‘StartEnd’ has only Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ‘StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Single-Date with Time, Check whether is Same with Start or Not
			
			If ‘StartEnd’ has Single-Date with time value, add a check whether ‘Start’ is same with ‘StartEnd’ date and time:
				
				#If StartEnd and Start are Same, Update End and StartEnd to `Default Time`
				
				If both ‘Start’ and ‘StartEnd’ have same Single-date and time, update ‘End’ accordingly `Default Setting` by adding one more hour later than ‘Start’ time and update ’StartEnd’ as Date-Range accordingly ‘Start’ and ‘End’ modified dates and times.
					
					#If StartEnd and Start are Not Same, Update End to `Default Time` and Overwrite StartEnd
					
					Otherwise, If both ‘Start’ and ‘StartEnd’ do not have same Single-date and time, update ’StartEnd’ as Date-Range accordingly `Default Setting` by adding one more hour later than its own existing time as endDate and entirely overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ modified dates and times. After that, overwrite ‘Last Updated Time’ accordingly current time.
			
			#If StartEnd has only Single-Date without Time, Check whether is Same with Start or Not
								
			If ‘StartEnd’ has only Single-Date without time value, add a check whether ‘Start’ is same with ‘StartEnd’:
				
				#All-Day-Event is Purposely Created from GCal
				#If StartEnd and Start are Same, Overwrite End and StartEnd to `Default Time`
				
				If both ‘Start’ and ‘StartEnd’ have only same Single-Date without time, overwrite ‘End’ accordingly ‘Start’ and ‘StartEnd’ same date without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#All-Day-Event is Modified from GCal
					#If StartEnd and Start are Not Same, Overwrite Start and End
					
					Otherwise, If both ‘Start’ and ‘StartEnd’ do not have same Single-Date, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing date without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
			
		#If StartEnd has Complete Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Date-Range with Time, Check whether is Same with Start or Not 
			
			If ‘StartEnd’ has Date-Range with time value, add a check whether ‘Start’ is same with ‘StartEnd’ date and time:
				
				#If StartEnd and Start are Same, Overwrite End
					
				If ‘Start’ is same with ‘StartEnd’ startTime, overwrite ‘End’ accordingly ’StartEnd’ endDate and time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#New Task is Scheduled Purposedly for Time-Blocking
					#If StartEnd and Start are Not Same, Overwrite Start and End
					
					Otherwise, If ‘Start’ is not same with ‘StartEnd’ startTime, overwrite ’Start’ and ‘End’ accordingly ’StartEnd’ existing time-range. After that, overwrite ‘Last Updated Time’ accordingly current time.
			
			#If StartEnd has only Date-Range without Time, Check whether is Same with Start or Not
			
			If ‘StartEnd’ has only Date-Range without time value, add a check whether ‘Start’ is same with ‘StartEnd’:
				
				#All-Day-Event is Purposely Scheduled from GCal
				#If StartEnd and Start are Same, Overwrite End				
				If ‘Start’ is same with ‘StartEnd’ startDate without time, overwrite ‘End’ accordingly ‘StartEnd’ endDate without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#All-Day-Event is Purposely Scheduled from GCal
					#If StartEnd and Start are Not Same, Overwrite Start and End					
					Otherwise, If ‘Start’ is not same with ‘StartEnd’ startDate without time, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ date-range. After that, overwrite ‘Last Updated Time’ accordingly current time.

			


`CONDITION C`: where ‘Start’ Date Property is always `None`

First Half

In this portion, ’GCalNeedUpdate’ is always `True`. This means when the requirements are met, ‘Start’ or / and ‘End’ Date Properties should always overwrite ‘StartEnd’ Date Property, however, ‘StartEnd’ should never overwrite ‘Start’ and ‘End’ Date Properties UNLESS there’s exception for First Half of CONDITION C.

#either New Task is Created or Existing Task is Modified from Notion

When ‘GCalNeedUpdate’ is `True`:
	
	
	#When Start, End and StartEnd are Empty, you might want to Sync All from `None` to `Default Time Range`
	
	if ‘Start’, ‘End’ and ‘StartEnd’ are all `None`, overwrite ‘Start’ Default Time to Today 08:00 and ‘End’ Default Time to Today 09:00. 
	After that, update ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. 
	Print those page(s’) ‘task_name’ which match the requirements and followed by its modified dates and times ( in standard format “MMM D, YYYY HH:mm” ).
	In the next newline, print “Number of Pages set Default Time Range: ” followed by total result of its “incremental value”. 
	
	#If only End is Present, Check whether has Time or Not
	
	If ‘Start’ and ‘StartEnd’ are both `None` whilst ‘End’ is not `None`, add a check whether ‘End’ has only Single-Date with or without specific time:
		
		#If End has Single-Date with Time, Sync StartEnd and Start from `None` to `Default Time Range`
		
		If ‘End’ has Single-Date with time value, overwrite ‘StartEnd’ endDate accordingly and subtract an hour earlier than ‘End’ time to set as ’StartEnd’ startDate whilst the same date and time value also applies to ‘Start’.
			
			#If End has Only Date, maybe is Mistake, Sync All from `None` to `Default Time Range`
			
			Otherwise, if ‘End’ has only Single-Date without time value, then update ‘StartEnd’ endDate, ‘Start’ and ‘End’ accordingly `Default Setting`.
	

		
	#When Only StartEnd is present, Check whether has Single-Date or Date-Range
	
	If ‘Start’ and ‘End’ are both `None` whilst ‘StartEnd’ is not `None`, add a check whether ‘StartEnd’ has Single-Date or Date-Range:
		
		#If StartEnd has Only Single-Date, Check whether has Time or Not
		
		If ’StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has specific time value or not:
			
			#If StartEnd has Single-Date with Time, Update StartEnd Only
			
			If ‘StartEnd’ has Single-Date with time value, update ‘StartEnd’ endDate accordingly `Default Setting` by not updating or affecting ‘Start’ and ‘End’.
				
				#If StartEnd has Only Single-Date without Time, Skip
				
				Otherwise, do nothing.
		
		#If StartEnd has Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ startDate and endDate have specific time value or not:
			
			#New Task is Scheduled Purposedly for Time Tracking
			
			Following sub-condition is the exception for First Half of `CONDITION C` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
				
				#If StartEnd has Date-Range with Time, Overwrite Start and End
			
				If ‘StartEnd’ has Date-Range with time values, overwrite both ‘Start’ and ‘End’ accordingly ‘StartEnd’ Time-Range. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#All-Day-Event is Purposely Scheduled
					
					Otherwise, If ‘StartEnd’ has Date-Range without time values, update ‘Start’ and ‘End’ accordingly ‘StartEnd’ Date-Range without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
	
	
		
	#In Case StartEnd was Set Up or Synchronised with Start and End Incompletely
	#End Shall Not Be Standalone without Start
	#If End and StartEnd are Present, Check whether StartEnd has Single-Date or Date-Range

	If only ‘Start’ is `None` whilst both ‘End’ and ‘StartEnd’ are not `None`, add a check whether ‘StartEnd’ has only Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ‘StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Single-Date with Time, Check whether is Same with End or Not
			
			If ‘StartEnd’ has Single-Date with time value, add a check whether ‘End’ is same with ‘StartEnd’ date and time:
				
				Following sub-condition is the exception for First Half of `CONDITION C` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
					
					#If Start is None When End is Same with StartEnd endDate and Time, is a Mistake, Instead Should be Updated
					#If StartEnd and End are Same, Update Start
					
					If both ‘End’ and ‘StartEnd’ have same Single-date and time, update ’Start’ accordingly `Default Setting` by subtracting an hour earlier than ’End’ existing time and entirely overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
						
						#If StartEnd and End are Not Same, Check whether End has Time or Not
						
						If ‘End’ is not same with ‘StartEnd’, add a check whether ‘End has time value or not.
							
							#If End has Time, Overwrite End and Update Start
							
							If ‘End’ has Single-Date with time value, update ’Start’ accordingly `Default Setting` by subtracting an hour earlier than ’End’ existing time and entirely overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
							
								#If End has Only Single-Date without Time, Update Start to `Default Time` and Overwrite StartEnd
								
								Otherwise, If ‘End’ has Single-Date without time value, update ‘Start’ and ‘End’ accordingly `Default Setting` and overwrite ‘StartEnd’ as time-range accordingly ‘Start’ and End’ modified dates and times.
			
			#If StartEnd has only Single-Date without Time, Check whether is Same with End or Not
								
			If ‘StartEnd’ has only Single-Date without time value, add a check whether ‘End’ is same with ‘StartEnd’:
				
				#If StartEnd and End are Same, Overwrite Start and StartEnd to `Default Time`
				
				If both ‘End’ and ‘StartEnd’ have only same Single-Date without time, overwrite ‘End’ and ‘Start’ accordingly `Default Setting` and then ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
					
					#If StartEnd and End are Not Same, Check whether End has Time or Not
					
					If ‘End’ is not same with ‘StartEnd’, add a check whether ‘End’ has time value or not.
						
						#If End has Time, Update Start to `Default Time` and Overwrite StartEnd
						
						If ‘End’ has Single-Date with time value, update ‘Start’ accordingly `Default Setting` by subtracting an hour earlier than ‘End’ and then overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
							
							#If End has Only Single-Date without Time, Update Start and End to `Default Time` and Overwrite StartEnd
							
							Otherwise, If ‘End’ has Single-Date without time value, update ’Start and ‘End’ accordingly `Default Setting` and overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
			
		#If StartEnd has Complete Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Date-Range with Time, Check whether is Same with End or Not 
			
			If ‘StartEnd’ has Date-Range with time value, add a check whether ‘End’ is same with ‘StartEnd’ date and time:
				
				#New Task is Scheduled Purposedly for Time-Blocking
				
				Following sub-condition is the exception for First Half of `CONDITION C` that ‘StartEnd’ is allowed to overwrite ‘Start’ and ‘End’:
					
					#If StartEnd and End are Same, Overwrite Start
					
					If ‘End’ is same with ‘StartEnd’ endTime, overwrite ‘Start’ accordingly ’StartEnd’ startDate and time. After that, overwrite ‘Last Updated Time’ accordingly current time.
						
						#If StartEnd and End are Not Same, Update Start and Overwrite StartEnd
						
						Otherwise, If ‘End’ is not same with ‘StartEnd’ endTime, update ’Start’ accordingly an hour earlier than ’End’ existing time then overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
			
			#If StartEnd has only Date-Range without Time, Check whether is Same with End or Not
			
			If ‘StartEnd’ has only Date-Range without time value, add a check whether ‘End’ is same with ‘StartEnd’:
				
				#If StartEnd and End are Same, Overwrite Start and End to `Default Time` and StartEnd to `Default Time Range`
				
				If ‘End’ is same with ‘StartEnd’ endDate without time, overwrite ‘End’ and ‘Start’ accordingly `Default Setting` and ‘StartEnd’ accordingly `Default Setting`.
					
					#If StartEnd and End are Not Same, Overwrite Start and End to `Default Time` and Overwrite StartEnd
					
					Otherwise, overwrite ‘End’ and ‘Start’ accordingly its `Default Setting` and ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.



Second Half

In this portion,‘GCalNeedUpdate’ is always `False`. This means when the requirements are met, ‘StartEnd’ Date Property should always overwrite ‘Start’ or / and ‘End’ Date Properties, however, ‘Start’ or / and ‘End’ Date Properties should never overwrite ‘StartEnd’ Date Property UNLESS there’s exception for Second Half of CONDITION C.

#either New Task is Created or Existing Task is Modified from GCal

When ‘GCalNeedUpdate’ is `False`:



	#When Start, End and StartEnd are Empty, You Might Want to Sync All from `None` to `Default Time Range`
	
	if ‘Start’, ‘End’ and ‘StartEnd’ are all `None`, overwrite ‘StartEnd’ default time to Today 08:00 and 09:00. 
	After that, update ‘Start’ and ‘End’ accordingly ‘StartEnd’ modified dates and times.
	Print those page(s’) ‘task_name’ which match the requirements and followed by modified dates and times ( in standard format “MMM D, YYYY HH:mm” ).
	In the next newline, print “Number of Pages set Default Time Range: ” followed by total result of its “incremental value”. 
	
	#If only End is Present, Check whether has Time or Not
	
	If ‘Start’ and ‘StartEnd’ are both `None` whilst ‘End’ is not `None`, add a check whether ‘End’ has only Single-Date with or without specific time:
		
		#If End has Time, Only Update Start to `Default Time`
		
		If ‘End’ has time value, update ‘Start’ accordingly by subtracting an hour earlier than ‘End’ time by not updating or affecting ‘StartEnd.
			
			#If End has Only Single-Date, Update Start and End to `Default Time`
			
			Otherwise, if ‘End’ has only Single-Date without time value, then update ‘Start’ and ‘End’ accordingly `Default Setting` by not updating or affecting ‘StartEnd’. 
	
	
	
	#When only StartEnd is Present, Check whether has Single-Date or Date-Range
	
	If ‘Start’ and ‘End’ are both `None` whilst ‘StartEnd’ is not `None`, add a check whether ‘StartEnd’ has Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ’StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has specific time value or not:
			
			#If StartEnd has Single-Date with Time, maybe is Mistake, Overwrite Start, End and StartEnd to `Default Time` 
			
			If  ‘StartEnd’ has Single-Date with time value, overwrite ‘Start’, ‘End’ and ‘StartEnd’ endDate accordingly `Default Setting`.
				
				#All-Day-Event is Purposely Scheduled from GCal
				#If StartEnd has Only Single-Date without Time, Overwrite Start, End and StartEnd to `Default Time`
				
				Otherwise, overwrite entirely ‘StartEnd’, ‘Start’ and ‘End’ accordingly its `Default Setting`.
		
		#If StartEnd had Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ startDate and endDate have specific time value or not:
			
			#New Task is Created for Detailed Time-Blocking from GCal
			#If StartEnd has Date-Range with Time, Skip
			
			If ‘StartEnd’ has Date-Range with time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing dates and times. After that, overwrite ‘Last Updated Time’ accordingly current time.
				
				#New Task is Created for Days-Blocking from GCal
				#If StartEnd has Only Date-Range without Time, Overwrite StartEnd
				
				Otherwise, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing dates only without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
	
	
		
	#In Case StartEnd was Set Up or Synchronised with Start and End Incompletely, is a Mistake
	#End Shall Not Be Standalone without Start
	#If End and StartEnd are Present, Check whether StartEnd has Single-Date or Date-Range

	If only ‘Start’ is `None` whilst both’ End’ and ‘StartEnd’ are not `None`, add a check whether ‘StartEnd’ has only Single-Date or Date-Range:
		
		#If StartEnd has only Single-Date, Check whether has Time or Not
		
		If ‘StartEnd’ has Single-Date only, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Single-Date with Time, Check whether is Same with End or Not
			
			If ‘StartEnd’ has Single-Date with time value, add a check whether ‘End’ is same with ‘StartEnd’ date and time:
				
				#If StartEnd and End are Same, Update Start and StartEnd to `Default Time`
				
				If both ‘End’ and ‘StartEnd’ have same Single-date and time, update ‘Start’ accordingly `Default Setting` by subtracting an hour earlier than ‘End’ time and update ’StartEnd’ as Date-Range accordingly ‘Start’ and ‘End’ modified dates and times.
					
					#If StartEnd and End are Not Same, Update Start to `Default Time` and Overwrite StartEnd
					
					Otherwise, update ’Start’ accordingly `Default Setting` by subtracting an hour earlier than ’End’ existing time and entirely overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
			
			#If StartEnd has only Single-Date without Time, Check whether is Same with End or Not
								
			If ‘StartEnd’ has only Single-Date without time value, add a check whether ‘End’ is same with ‘StartEnd’:
				
				#If StartEnd and End are Same, Overwrite Start and StartEnd to `Default Time`
				
				If both ‘End’ and ‘StartEnd’ have only same Single-Date without time, overwrite ‘End’ and ‘Start’ accordingly `Default Setting` and then ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
					
					#If StartEnd and End are Not Same, Overwrite Start and StartEnd to `Default Time`
					
					Otherwise, overwrite ‘End’ and ‘Start’ accordingly `Default Setting` and then ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
			
		#If StartEnd has Complete Date-Range, Check whether has Time or Not
		
		If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ has time value or not:
			
			#If StartEnd has Date-Range with Time, Check whether is Same with End or Not 
			
			If ‘StartEnd’ has Date-Range with time value, add a check whether ‘End’ is same with ‘StartEnd’ date and time:
				
				#If StartEnd and End are Same, Overwrite Start
					
				If ‘End’ is same with ‘StartEnd’ endTime, overwrite ‘Start’ accordingly ’StartEnd’ startDate and time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#New Task is Scheduled Purposedly for Time-Blocking
					#If StartEnd and End are Not Same, Overwrite Start and End
					
					Otherwise, overwrite ’Start’ and ‘End’ accordingly ’StartEnd’ existing time-range. After that, overwrite ‘Last Updated Time’ accordingly current time.
			
			#If StartEnd has only Date-Range without Time, Check whether is Same with End or Not
			
			If ‘StartEnd’ has only Date-Range without time value, add a check whether ‘End’ is same with ‘StartEnd’:
				
				#All-Day-Event is Purposely Scheduled
				#If StartEnd and End are Same, Overwrite Start and End				
				If ‘End’ is same with ‘StartEnd’ endDate without time, overwrite ‘Start’ accordingly ‘StartEnd’ startDate without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
					
					#All-Day-Event is Purposely Scheduled
					#If StartEnd and End are Not Same, Overwrite Start and End
					
					Otherwise, If ‘End’ is not same with ‘StartEnd’ endDate, overwrite ‘End’ and ‘Start’ accordingly ‘StartEnd’ date-range. After that, overwrite ‘Last Updated Time’ accordingly current time.







CONDITION D: where ‘Start’, End’ and ‘StarEnd’ Date Property are not `None`


First Half

In this portion, ’GCalNeedUpdate’ is always `True`. This means when the requirements are met, ‘Start’ or / and ‘End’ Date Properties should always overwrite ‘StartEnd’ Date Property, however, ‘StartEnd’ should never overwrite ‘Start’ and ‘End’ Date Properties UNLESS there’s exception for First Half of CONDITION D.

#either New Task is Created or or Existing Task is Modified from Notion

When ‘GCalNeedUpdate’ is `True`:


	#When Start, End and StartEnd are not Empty, You Might Want to Check whether Are All Same or Not
	
	If ‘Start’, ‘End’ and ‘StartEnd’ are not `None`,  add a check whether if ‘StartEnd’ is same with ‘Start’ and ‘End’.
		
 		#If StartEnd is same with Start and End, Skip
		
		If ‘StartEnd’ is same with both ‘Start’ and ‘End’, do noting.
			
			#if StartEnd is not same with Start and End, Check whether Start and End have Single-Date or Date-Range
			
			If either ‘Start’ or ‘End’ is not same with ‘StartEnd’, add a check whether ‘Start’ and ‘End’ has Single-Date or Date-Range
			
				#If Start and End have Single-Date, Check whether Start and End have Time or Not
				
				If ‘Start’ and ‘End’ have Single-Date, add a check whether ‘Start’ and ‘End’ have time value or not.

					#If Start and End have Single-Date with Time, Check whether End is same with Start

					If ‘Start’ and ‘End’ have Single-Date with time value, add a check whether ‘End’ is same with ‘Start’

						#If End is same with Start, Update End and Overwrite StartEnd
						
						If ‘End’ is same with ‘Start’, update ‘End’ accordingly `Default Setting` by adding one more hour later than ‘Start’ existing time and then overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
							
							#If End is not same with Start, Overwrite StartEnd
							
							If ‘End’ is not same with ‘Start’, overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ existing dates and times.

					
					#All-Day-Event is modified from Notion
					#If Start and End have Only Single-Date without Time, Overwrite StartEnd
					
					If both ‘Start’ and ‘End’ have only Single-Date without time value, overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ existing date without time.

										
					#If only either Start or End has Single-Date with Time, Check whether End is same with Start

					If only ‘Start’ has Single-Date with time value, overwrite ‘End’ accordingly `Default Setting` by adding one more hour later than ‘Start’ time and then ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times. Otherwise, If only ‘End’ has Single-Date with time value, overwrite ‘Start’ accordingly `Default Setting` by subtracting an hour earlier than ‘End’ time and then overwrite ‘StartEnd’ accordingly ‘Start’ and ‘End’ modified dates and times.
					
		
				
			
Second Half

In this portion,‘GCalNeedUpdate’ is always `False`. This means when the requirements are met, ‘StartEnd’ Date Property should always overwrite ‘Start’ or / and ‘End’ Date Properties, however, ‘Start’ or / and ‘End’ Date Properties should never overwrite ‘StartEnd’ Date Property UNLESS there’s exception for Second Half of CONDITION D.

#either New Task is Created or Existing Task is Modified from GCal

When ‘GCalNeedUpdate’ is `False`:


	#When Start, End and StartEnd are not Empty, You Might Want to Check whether Are All Same or Not
	
	If ‘Start’, ‘End’ and ‘StartEnd’ are not `None`,  add a check whether if ‘Start’ and ‘End’ are same with ‘StartEnd’.
		
 		#If Start and End are same with StartEnd, Skip
		
		If both ‘Start’ and ‘End’ are same with ‘Start’ and ‘End’, do noting.
			
			#if either Start or End is not same with StartEnd, Check whether StartEnd has Single-Date or Date-Range
			
			If either ‘Start’ or ‘End’ is not same with ‘StartEnd’, add a check whether ‘StartEnd’ has Single-Date or Date-Range
			
				#If StartEnd has Single-Date, Check whether StartEnd has Time or Not
				
				If ‘StartEnd’ has Single-Date, add a check whether ‘StartEnd’ has time value or not.

					#If StartEnd has Single-Date with Time, Update StartEnd and Overwrite Start and End

					If ‘StartEnd’ has Single-Date with time value, update ‘StartEnd’ endDate accordingly `Default Setting` by adding one more hour later than ‘StartEnd’ existing date and time and then overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ modified dates and times. After that, overwrite ‘Last Updated Time’ accordingly current time.

						#All-Day-Event is modified from GCal
						#If StartEnd has Only Single-Date without Time, Overwrite Start and End
						
						If ‘StartEnd’ has only Single-Date without time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ same date without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
						
			
				#If StartEnd has Date-Range, Check whether StartEnd has Time or Not
				
				If ‘StartEnd’ has Date-Range, add a check whether ‘StartEnd’ has time value or not.

					#If StartEnd has Date-Range with Time, Update StartEnd and Overwrite Start and End

					If ‘StartEnd’ has Date-Range with time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ existing dates and times. After that, overwrite ‘Last Updated Time’ accordingly current time.

						#Days-Blocking is modified from GCal
						#If StartEnd has Only Date-Range without Time, Overwrite Start and End
						
						Otherwise, If ‘StartEnd’ has only Date-Range without time value, overwrite ‘Start’ and ‘End’ accordingly ‘StartEnd’ same Date-Range without time. After that, overwrite ‘Last Updated Time’ accordingly current time.
	










