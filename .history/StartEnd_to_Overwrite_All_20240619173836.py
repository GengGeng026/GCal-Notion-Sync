if(prop("StartEnd == empty") == true, false,
	/* Check, ONLY StartEnd is Present */
	if( 
		(prop("StartEnd == empty") == false) 
		/* AND */ 
		and 
		(
			/*Start + End + PrevStart + PrevEnd are ALL Empty */
			(prop("Start == empty") == true) and (prop("End == empty") == true) and (prop("PrevStart == empty") == true) and (prop("PrevEnd == empty") == true)
		)
		/* OR */
		or 
		(
			/*Start OR End OR PrevStart OR PrevEnd is Empty */
			(prop("Start == empty") == true) or (prop("End == empty") == true) or (prop("PrevStart == empty") == true) or (prop("PrevEnd == empty") == true)
		), true,

		/* StartEnd AND ALL are Present */
		if( ((prop("StartEnd == empty") == false) and (prop("Start == empty") == false) and (prop("End == empty") == false) and (prop("PrevStart == empty") == false) and (prop("PrevEnd == empty") == false))
			
			/* AND */
			and 
			(
				
				(
				/* Start = PrevStart 
				   AND End = PrevEnd */
				(prop("Start = Prev_Start") == true and prop("End = Prev_End") == true)
				)
				
				/* AND */
				and 
			
				/* StartEnd != Start */
				( 
					prop("StartEnd == Start") == false 
						
					/* AND */
					and 
					(
						/* No Time AND No EndDate AND No Range */
						( prop("S.End No TIme") == true and prop("S.End has EndDate") == false and prop("S.End got Range") == false ) 
						/* OR No Time AND has EndDate AND got Range AND is 00:00 AND StartEnd == End */
						or ( prop("S.End No TIme") == true and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == false and prop("StartEnd == End") == true ) 
						/* OR No Time AND has EndDate AND got Range AND is 00:00 AND StartEnd == End */
						or ( prop("S.End No TIme") == true and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == false and prop("StartEnd == End") == false) 
						/* OR No TIme AND Has EnDate AND got Range AND not 00:00 */
						or ( prop("S.End No TIme") == false and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true ) 
					)
				
					or 
					/* StartEnd == Start AND STartEnd != End */
					( 
						prop("StartEnd == Start") == true
						and 
						/* AND No Time AND No EndDate AND No Range AND is 00:00 */
						(
							( prop("S.End No TIme") == true and prop("S.End has EndDate") == false and prop("S.End got Range") == false and prop("S.End 00:01—23:59") == false and prop("StartEnd == End") == false )
							or 
							/* OR No Time AND has EndDate AND got Range AND is 00:00 AND StartEnd != End */
							( prop("S.End No TIme") == true and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == false and prop("StartEnd == End") == false )
							or 
							/* OR has Time AND has EndDate AND got Range AND is 00:00 AND StartEnd != End */
							( prop("S.End No TIme") == false and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true and prop("StartEnd == End") == false )
						)
					)
				)
			)
			
			/* OR */
			or 
			(
				
				(
				/* Start = PrevStart 
				   OR End = PrevEnd */
				(prop("Start = Prev_Start") == true and prop("End = Prev_End") == true)
				)
					
					/* AND */
					and 
			
					/* StartEnd != PrevStart AND StartEnd != PrevEnd */
					( 
							prop("StartEnd == PrevStart") == false and prop("StartEnd == PrevEnd") == false
					)
					
					/* AND */
					and 
			
					/* StartEnd != Start AND StartEnd != End */
					( 
							prop("StartEnd == Start") == false or prop("StartEnd == End") == false
					)
					
						and 
					/* AND */
					(
							/* No Time AND No EndDate AND No Range */
							( prop("S.End No TIme") == true and prop("S.End has EndDate") == false and prop("S.End got Range") == false ) 
							/* OR No Time AND has EndDate AND got Range AND is 00:00 AND StartEnd == End */
							or ( prop("S.End No TIme") == true and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == false and prop("StartEnd == End") == true ) 
								/* OR No TIme AND Has EnDate AND got Range AND not 00:00 */
								or ( prop("S.End No TIme") == false and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true )
						)
			)

			/* OR */
			or 
			(
				
				(
				/* Start != PrevStart 
				   AND End != PrevEnd */
				(prop("Start = Prev_Start") == false and prop("End = Prev_End") == false)
				)
					
					/* AND */
					and 
			
					/* StartEnd == Start AND StartEnd == End */
					( 
							(prop("StartEnd == Start") == true or prop("StartEnd == End") == true)
					)
					or 
					( 
							/* StartEnd != Start AND StartEnd != End */
							(prop("StartEnd == Start") == false and prop("StartEnd == End") == false) 
							/* AND StartEnd != PrevStart AND StartEnd != PrevEnd */
							and (prop("StartEnd == PrevStart") == false and prop("StartEnd == PrevEnd") == false)
					)
						and 
					/* AND */
					(
							/* No Time AND No EndDate AND No Range */
							( prop("S.End No TIme") == true and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true ) 
					)
			)

			/* OR */
			or 
			(
				
				(
				/* Start != PrevStart 
				   AND End != PrevEnd */
				(prop("Start = Prev_Start") == false or prop("End = Prev_End") == false)
				)
					
					/* AND */
					and 
			
					/* StartEnd != PrevStart AND StartEnd != PrevEnd */
					( 
							prop("StartEnd == PrevStart") == true and prop("StartEnd == PrevEnd") == true
					)
					
						/* AND */
						and 
				
						/* StartEnd != Start AND Start No Time */
						( 
								prop("StartEnd == Start") == false and prop("Start No Time") == true
						)
							and 
						/* AND */
						(
								/* No Time AND No EndDate AND got Range AND not 00:00 AND StartEnd = End */
								( prop("S.End No TIme") == false and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true and prop("StartEnd == End") == true )
						)
						
						/* OR */
						or 
				
						/* StartEnd == Start AND End No Time */
						( 
								prop("StartEnd == Start") == true and prop("End No Time") == true
						)
							and 
						/* AND */
						(
								/* No Time AND No EndDate AND got Range AND not 00:00 AND StartENd != End */
								( prop("S.End No TIme") == false and prop("S.End has EndDate") == true and prop("S.End got Range") == true and prop("S.End 00:01—23:59") == true and prop("StartEnd == End") == false )
						)
			)
				, true, false)))