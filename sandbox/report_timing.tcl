report_timing -delay_type min_max -max_paths 10 -slack_less_than 0 -sort_by group -input_pins -name timing_3

set failing_paths [get_timing_paths -delay_type min_max -max_paths 10 -slack_less_than 0 -sort_by group]
report_property [lindex $failing_paths 0]