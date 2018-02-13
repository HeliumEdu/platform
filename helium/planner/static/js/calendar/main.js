/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript functionality for persistence and the HeliumCalendar object on the /planner/calendar page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.3.4
 */

/**
 * Create the HeliumCalendar persistence object.
 *
 * @constructor construct the HeliumCalendar persistence object
 */
function HeliumCalendar() {
    "use strict";

    this.DEFAULT_VIEWS = ["month", "agendaWeek", "agendaDay", "list"];
    this.DONE_TYPING_INTERVAL = 500;
    this.QTIP_SHOW_INTERVAL = 250;
    this.QTIP_HIDE_INTERVAL = 500;

    this.loading_div = null;

    this.ajax_calls = [];
    this.last_view = null;
    this.edit = false;
    this.init_calendar_item = false;
    this.current_class_id = -1;
    this.start = null;
    this.end = null;
    this.all_day = null;
    this.show_end_time = null;
    this.current_calendar_item = null;
    this.preferred_material_ids = null;
    this.preferred_category_name = null;
    this.preferred_category_id = -1;
    this.reminder_unsaved_pk = 0;
    this.typing_timer = 0;
    this.last_good_grade = "";
    this.last_type_event = false;
    this.last_good_date = null;
    this.last_good_end_date = null;
    this.last_search_string = "";
    this.dropzone = null;
    this.is_resizing_calendar_item = false;
    this.listViewLoaded = false;
    this.course_groups = {};
    this.courses = {};

    var self = this;

    /*******************************************
     * Functions
     ******************************************/

    /**
     * Revert persistence for adding/editing a Homework.
     */
    this.nullify_calendar_item_persistence = function () {
        self.edit = false;
        self.start = null;
        self.end = null;
        self.current_class_id = -1;
        self.current_course_group_id = -1;
        self.all_day = null;
        self.show_end_time = null;
        self.current_calendar_item = null;
        self.preferred_category_name = null;
        self.preferred_material_ids = null;
        self.preferred_category_id = -1;
        self.reminder_unsaved_pk = 0;
        self.last_good_grade = "";
        self.is_resizing_calendar_item = false;
        helium.ajax_error_occurred = false;
    };

    /**
     * Clear Homework marked in the Homework modal.
     */
    this.clear_calendar_item_errors = function () {
        helium.ajax_error_occurred = false;
        $("#homework-title").parent().parent().removeClass("has-error");
        $("#homework-start-date").parent().parent().removeClass("has-error");
        $("#homework-end-date").parent().parent().removeClass("has-error");
        $("#homework-category").parent().parent().removeClass("has-error");
    };

    /**
     * Retrieve the course from the given list with the given ID.
     *
     * @param courses the list of courses
     * @param pk the key to look for
     */
    this.get_course_from_list_by_pk = function (courses, pk) {
        var i = 0, course = null;

        for (i = 0; i < courses.length; i += 1) {
            if (courses[i].id === parseInt(pk)) {
                course = courses[i];
                break;
            }
        }

        return course;
    };

    /**
     * Retrieve the name for the given category ID.
     *
     * @param id the ID of the category
     * @return the name of the category, null if the category is not available
     */
    this.get_category_name_by_id = function (id) {
        var category_options = $("#homework-category").find("option"), name = null, option, i = 0;
        for (i = 0; i < category_options.length; i += 1) {
            option = $(category_options[i]);
            if (parseInt(option.val()) === parseInt(id)) {
                name = option.html();
                break;
            }
        }

        return name;
    };

    /**
     * Retrieve the ID for the given category name.
     *
     * @param name the name of the category
     * @return the ID of the category, -1 if the category is not available
     */
    this.get_category_id_by_name = function (name) {
        var id = -1, category_options = $("#homework-category").find("option"), i = 0, option;
        for (i = 0; i < category_options.length; i += 1) {
            option = $(category_options[i]);
            if (option.html() === name) {
                id = option.val();
                break;
            }
        }
        return id;
    };

    /**
     * Clear any used cookies.
     */
    this.clear_filter_cookies = function () {
        Cookies.remove("filter_show_homework", {path: "/"});
        Cookies.remove("filter_show_events", {path: "/"});
        Cookies.remove("filter_show_external", {path: "/"});
        Cookies.remove("filter_show_class", {path: "/"});
        Cookies.remove("filter_search_string", {path: "/"});
        Cookies.remove("filter_categories", {path: "/"});
        Cookies.remove("filter_complete", {path: "/"});
        Cookies.remove("filter_overdue", {path: "/"});
    };

    /**
     * Drop an event after it is finished being dragged.
     *
     * @param event the event being dropped
     */
    this.drop_calendar_item = function (event) {
        var all_day = false;
        if (!event.start.hasTime()) {
            all_day = true;
        }

        event.start = $("#calendar").fullCalendar("getCalendar").moment(moment(event.start.format()).format());
        event.end = $("#calendar").fullCalendar("getCalendar").moment(moment(event.end.format()).format());

        helium.ajax_error_occurred = false;

        self.loading_div.spin(helium.SMALL_LOADING_OPTS);

        self.current_calendar_item = event;
        var callback = function (data) {
            if (helium.data_has_err_msg(data)) {
                helium.ajax_error_occurred = true;
                self.loading_div.spin(false);

                bootbox.alert(helium.get_error_msg(data));
            } else {
                // If start does not have a time, this is an all day event
                if (!self.current_calendar_item.start.hasTime()) {
                    var start_end_days_diff = self.current_calendar_item.end ? self.current_calendar_item.end.diff(self.current_calendar_item.start, "days") : 1;
                    self.start = self.current_calendar_item.start;
                    self.end = self.current_calendar_item.start.hasTime() ? self.current_calendar_item.end : (start_end_days_diff <= 1 ? self.current_calendar_item.start.clone().add(helium.USER_PREFS.settings.all_day_offset, "minutes") : self.current_calendar_item.end.clone());
                } else {
                    self.start = self.current_calendar_item.start;
                    self.end = self.current_calendar_item.end || self.current_calendar_item.start.clone().add(helium.USER_PREFS.settings.all_day_offset, "minutes");
                }
            }
        };
        if (event.calendar_item_type === 0) {
            self.ajax_calls.push(helium.planner_api.get_event(callback, event.id));
        } else {
            var course = helium.calendar.courses[event.course];

            self.ajax_calls.push(helium.planner_api.get_homework(callback, course.course_group, course.id, event.id));
        }

        $.when.apply(this, self.ajax_calls).done(function () {
            if (!helium.ajax_error_occurred) {
                var data = {
                    "start": self.start.toISOString(),
                    "end": self.end.toISOString(),
                    "allDay": all_day,
                    "all_day": all_day
                };
                var callback = function (data) {
                    var calendar_item = data;

                    if (calendar_item.calendar_item_type === 0) {
                        calendar_item.id = "event_" + calendar_item.id;
                    }

                    self.update_current_calendar_item(calendar_item);

                    self.nullify_calendar_item_persistence();

                    self.loading_div.spin(false);
                };
                if (event.calendar_item_type === 0) {
                    helium.planner_api.edit_event(callback, event.id, data, true, true);
                } else {
                    var course = helium.calendar.courses[event.course];

                    helium.planner_api.edit_homework(callback, course.course_group, course.id, event.id, data, true, true);
                }
            }
        });
    };

    /**
     * Resize an event after it is finished being resized.
     *
     * @param event the event being resized
     */
    this.resize_calendar_item = function (event) {
        event.start = $("#calendar").fullCalendar("getCalendar").moment(moment(event.start.format()).format());
        event.end = $("#calendar").fullCalendar("getCalendar").moment(moment(event.end.format()).format());

        self.is_resizing_calendar_item = true;
        helium.ajax_error_occurred = false;

        var data;

        self.loading_div.spin(helium.SMALL_LOADING_OPTS);

        self.current_calendar_item = event;
        self.start = event.start;
        self.end = event.end;
        data = {
            "start": self.start.toISOString(),
            "end": self.end.toISOString()
        };
        var callback = function (data) {
            if (helium.data_has_err_msg(data)) {
                self.is_resizing_calendar_item = false;
                helium.ajax_error_occurred = true;
                self.loading_div.spin(false);

                bootbox.alert(helium.get_error_msg(data));
            } else {
                var calendar_item = data;

                if (calendar_item.calendar_item_type === 0) {
                    calendar_item.id = "event_" + calendar_item.id;
                }

                self.update_current_calendar_item(calendar_item);

                self.nullify_calendar_item_persistence();

                self.loading_div.spin(false);

                self.is_resizing_calendar_item = false;
            }
        };
        if (event.calendar_item_type === 0) {
            helium.planner_api.edit_event(callback, event.id, data, true, true);
        } else {
            var course = helium.calendar.courses[event.course];

            helium.planner_api.edit_homework(callback, course.course_group, course.id, event.id, data, true, true);
        }
    };

    /**
     * Clicking on the calendar triggers an event being added, which will bring up the Homework modal.
     *
     * @param start the start date/time of the event being added
     * @param end the end date/time of the event being added
     * @param event the jQuery event
     * @param view the current view of the calendar
     * @param calendar_item_type 0 for event, 1 for homework, 2 for course
     */
    this.add_calendar_item_btn = function (start, end, event, view, calendar_item_type) {
        calendar_item_type = typeof calendar_item_type === "undefined" ? self.last_type_event : calendar_item_type;

        var start_end_days_diff = end.diff(start, "days");
        self.init_calendar_item = true;
        self.edit = false;

        self.reminders_to_delete = [];
        self.attachments_to_delete = [];

        if ($("[id^='calendar-filter-course-']").length > 0) {
            $("#homework-event-switch").parent().show();
        } else {
            $("#homework-event-switch").parent().hide();

            calendar_item_type = 0;
        }
        $("#delete-homework").hide();
        $("#clone-homework").hide();
        $('a[href="#homework-panel-tab-1"]').tab("show");

        self.start = start;
        self.end = (start.hasTime && start.hasTime()) ? end : (start_end_days_diff <= 1 ? start.clone().add(helium.USER_PREFS.settings.all_day_offset, "minutes") : end.clone());
        self.all_day = start.hasTime && !start.hasTime();
        self.show_end_time = !self.all_day || (($("#calendar").fullCalendar("getView").name === self.DEFAULT_VIEWS[0] || $("#calendar").fullCalendar("getView").name === self.DEFAULT_VIEWS[1]) && start_end_days_diff > 1);
        // If we're adding an all-day event spanning multiple days, correct the end date to be offset by one
        if (self.all_day && !self.start.isSame(self.end, 'day')) {
            self.end = self.end.subtract(1, "days");
        }

        if ($("#homework-class").children().length <= 1) {
            $("#homework-class-form-group").hide("fast");
        } else {
            $("#homework-class-form-group").show("fast");
        }

        // Set the preferred IDs, which will be set when the global event is triggered selecting the course
        self.preferred_material_ids = null;
        self.preferred_category_id = -1;
        self.preferred_category_name = null;

        if ($("[id^='calendar-filter-course-']").length > 0) {
            $("#homework-class").trigger("change");
            $("#homework-class").trigger("chosen:updated");
        } else {
            self.start.hour(12);
            self.start.minute(0);
            if (!self.all_day) {
                self.end.hour(12);
                self.end.minute(50);
            } else {
                self.end.hour(12);
                self.end.minute(helium.USER_PREFS.settings.all_day_offset);
            }
        }

        if (calendar_item_type === 0) {
            $("#homework-event-switch").prop("checked", true).trigger("change");
        } else {
            $("#homework-event-switch").prop("checked", false).trigger("change");
        }

        $("#homework-title").val("");
        $("#homework-start-date").datepicker("setDate", self.start.toDate());
        $("#homework-end-date").datepicker("setDate", self.end.toDate());
        $("#homework-all-day").prop("checked", self.all_day).trigger("change");
        $("#homework-show-end-time").prop("checked", self.show_end_time).trigger("change");
        $("#homework-priority > span").slider("value", "50");
        $("#homework-completed").prop("checked", false).trigger("change");
        $("#homework-grade").val("");
        $("#homework-grade-percent > span").text("");
        $("#homework-comments").html("");

        $("tr[id^='attachment-']").remove();
        $("#no-attachments").show();
        if (self.dropzone !== null) {
            self.dropzone.removeAllFiles();
        }

        $("tr[id^='reminder-']").remove();
        $("#no-reminders").show();

        $("#loading-homework-modal").spin(false);
        $("#homework-modal").modal("show");
        $("#calendar").fullCalendar("unselect");
        self.init_calendar_item = false;
    };

    /**
     * Delete an attachment from the list of attachments.
     */
    this.delete_attachment = function () {
        var dom_id = $(this).attr("id");
        var id = dom_id.split("-");
        id = id[id.length - 1];
        helium.calendar.attachments_to_delete.push(id);

        if ($("#attachments-table-body").children().length === 1) {
            $("#no-attachments").show();
        }
        $("#attachment-" + $(this).attr("id").split("delete-attachment-")[1]).hide("fast", function () {
            $(this).remove();
            if ($("#attachments-table-body").children().length === 1) {
                $("#no-attachments").show();
            }
        });
    };

    this.on_day_of_week = function (schedule, day) {
        if (schedule == null) {
            return false;
        }

        return schedule.days_of_week.substring(day, day + 1) == '1';
    };

    this.same_time = function (schedule) {
        return (
            (schedule.sun_start_time == schedule.mon_start_time &&
            schedule.sun_start_time == schedule.tue_start_time &&
            schedule.sun_start_time == schedule.wed_start_time &&
            schedule.sun_start_time == schedule.thu_start_time &&
            schedule.sun_start_time == schedule.fri_start_time &&
            schedule.sun_start_time == schedule.sat_start_time)
            &&
            (schedule.sun_end_time == schedule.mon_end_time &&
            schedule.sun_end_time == schedule.tue_end_time &&
            schedule.sun_end_time == schedule.wed_end_time &&
            schedule.sun_end_time == schedule.thu_end_time &&
            schedule.sun_end_time == schedule.fri_end_time &&
            schedule.sun_end_time == schedule.sat_end_time)
        )
    };

    this.has_schedule = function (schedule) {
        return schedule.days_of_week != '0000000' || !self.same_time(schedule);
    };

    /**
     * Clicking on a calendar item on the calendar triggers an event being edited, which will bring up the Homework modal.
     *
     * @param calendar_item the homework or event being edited
     */
    this.edit_calendar_item_btn = function (calendar_item) {
        var h_e_str, h_e_id;

        helium.ajax_error_occurred = false;

        var ret_val = true, i = 0;
        // If what we've clicked on is an external source with a URL, open in a new window
        if (calendar_item.url !== undefined && calendar_item.url !== null) {
            window.open(calendar_item.url);
            ret_val = false;
        } else {
            h_e_str = calendar_item.calendar_item_type === 0 ? "event" : (calendar_item.calendar_item_type === 1 ? "homework" : "external");
            h_e_id = calendar_item.calendar_item_type === 0 ? calendar_item.id.substr(6) : calendar_item.id;

            if (($("#calendar").fullCalendar("getView").name === "list" || $("#calendar-" + h_e_str + "-checkbox-" + h_e_id).is(":checked") === calendar_item.completed || calendar_item.completed === undefined)) {
                // If the checkbox and homework field for "completed" match, the homework was clicked, so open the modal
                // Alternatively, if the "completed" field does not exist, this is an event, so open the model
                if (!self.edit) {
                    self.loading_div.spin(helium.SMALL_LOADING_OPTS);
                    self.init_calendar_item = true;
                    self.edit = true;

                    self.reminders_to_delete = [];
                    self.attachments_to_delete = [];

                    $("#homework-event-switch").parent().hide();
                    $("#delete-homework").show();
                    $("#clone-homework").show();

                    self.current_calendar_item = calendar_item;
                    // Initialize dialog attributes for editing
                    var callback = function (data) {
                        if (helium.data_has_err_msg(data)) {
                            helium.ajax_error_occurred = true;
                            self.loading_div.spin(false);
                            $("#loading-homework-modal").spin(false);
                            self.init_calendar_item = false;
                            self.edit = false;

                            bootbox.alert(helium.get_error_msg(data));
                        } else {
                            var calendar_item_fields = data;

                            // Change display to the correct course group tab
                            $('a[href="#homework-panel-tab-1"]').tab("show");

                            self.start = moment(calendar_item_fields.start);
                            self.end = moment(calendar_item_fields.end);
                            self.all_day = calendar_item_fields.all_day;
                            self.show_end_time = calendar_item_fields.show_end_time;
                            // If we're adding an all-day event spanning multiple days, correct the end date to be offset by one
                            if (self.all_day && !self.start.isSame(self.end, "day")) {
                                self.end = self.end.subtract(1, "days");
                            }

                            if ($("#homework-class").children().length <= 1 || $("#homework-event-switch").is(":checked")) {
                                $("#homework-class-form-group").hide("fast");
                            } else {
                                $("#homework-class-form-group").show("fast");
                            }

                            if (calendar_item_fields.calendar_item_type === 1) {
                                // Set the preferred IDs, which will be set when the global event is triggered selecting the course
                                self.preferred_material_ids = [];
                                $.each(calendar_item_fields.materials, function (index, material) {
                                    self.preferred_material_ids.push(material.id);
                                });
                                self.preferred_category_name = null;
                                self.preferred_category_id = calendar_item_fields.category;

                                $("#homework-class").val(helium.calendar.courses[calendar_item_fields.course].id);

                                // Triggering this class change is also what triggers the all day/end time checkboxes to be triggered
                                $("#homework-class").trigger("change");
                                $("#homework-class").trigger("chosen:updated");

                                $("#homework-event-switch").prop("checked", false).trigger("change");
                            } else {
                                $("#homework-event-switch").prop("checked", true).trigger("change");

                                // This function usually is triggered in #homework-class, but that won't get triggered for events
                                self.set_timing_fields();
                            }

                            $("#homework-title").val(calendar_item_fields.title);

                            $("#homework-start-date").datepicker("setDate", self.start.toDate());
                            $("#homework-end-date").datepicker("setDate", self.end.toDate());
                            $("#homework-all-day").prop("checked", calendar_item_fields.all_day).trigger("change");
                            $("#homework-show-end-time").prop("checked", calendar_item_fields.show_end_time).trigger("change");
                            $("#homework-priority > span").slider("value", calendar_item_fields.priority);
                            $("#homework-completed").prop("checked", calendar_item_fields.completed).trigger("change");
                            if (calendar_item_fields.calendar_item_type === 1) {
                                self.last_good_grade = calendar_item_fields.current_grade !== "-1/100" ? calendar_item_fields.current_grade : "";
                                $("#homework-grade").val(self.last_good_grade);
                                self.homework_render_percentage(self.last_good_grade);
                            } else {
                                $("#homework-grade-percent > span").text("");
                            }
                            $("#homework-comments").html(calendar_item_fields.comments);

                            $("tr[id^='attachment-']").remove();
                            if (calendar_item_fields.attachments.length === 0) {
                                $("#no-attachments").show();
                            } else {
                                $("#no-attachments").hide();
                            }
                            if (self.dropzone !== null) {
                                self.dropzone.removeAllFiles();
                            }

                            for (i = 0; i < calendar_item_fields.attachments.length; i += 1) {
                                $("#attachments-table-body").append("<tr id=\"attachment-" + calendar_item_fields.attachments[i].id + "\"><td>" + calendar_item_fields.attachments[i].title + "</td><td>" + helium.bytes_to_size(parseInt(calendar_item_fields.attachments[i].size)) + "</td><td><div class=\"btn-group\"><a class=\"btn btn-xs btn-success\" download target=\"_blank\" href=\"" + calendar_item_fields.attachments[i].attachment + "\"><i class=\"icon-cloud-download bigger-120\"></i></a> <button class=\"btn btn-xs btn-danger\" id=\"delete-attachment-" + calendar_item_fields.attachments[i].id + "\"><i class=\"icon-trash bigger-120\"></i></button></div></td></tr>");
                                $("#delete-attachment-" + calendar_item_fields.attachments[i].id).on("click", self.delete_attachment);
                            }

                            $("tr[id^='reminder-']").remove();
                            $("#no-reminders").show();

                            self.reminder_unsaved_pk = calendar_item_fields.reminders.length + 1;
                            for (i = 0; i < calendar_item_fields.reminders.length; i += 1) {
                                self.add_reminder_to_table(calendar_item_fields.reminders[i], false);
                            }

                            self.loading_div.spin(false);
                            $("#loading-homework-modal").spin(false);
                            $("#homework-modal").modal("show");
                            self.init_calendar_item = false;
                        }
                    };
                    if (calendar_item.calendar_item_type === 0) {
                        helium.planner_api.get_event(callback, calendar_item.id, true, false);
                    } else if (calendar_item.calendar_item_type === 1) {
                        var course = helium.calendar.courses[calendar_item.course];

                        helium.planner_api.get_homework(callback, course.course_group, course.id, calendar_item.id, true, false);
                    } else {
                        self.loading_div.spin(false);
                        self.init_calendar_item = false;
                        self.edit = false;
                    }
                }
            } else {
                // If the checkbox and homework field for "completed" don't match, the checkbox was clicked, so that trigger will handle the save
                self.current_calendar_item = calendar_item;
            }
        }

        return ret_val;
    };

    /**
     * Render the grade percentage display based on the given grade, assuming it should be shown.
     *
     * @param grade the grade string for display
     */
    this.homework_render_percentage = function (grade) {
        if (grade.indexOf("/") !== -1) {
            $("#homework-grade-percent > span").text(helium.grade_for_display(grade));
        } else if (grade.indexOf("%") !== -1) {
            // The grade is already prepped, so just display it
            $("#homework-grade-percent > span").text(grade);
        } else {
            $("#homework-grade-percent > span").text("");
        }
    };

    /**
     * Update filter checkbox given a click on the filter title.
     *
     * @param selector the selector for the filter title
     */
    this.update_filter_checkbox = function (selector) {
        var checkbox;
        $("#filter-button-title").html("Filter (On)");
        checkbox = $(selector.children()[0]);
        checkbox.prop("checked", !checkbox.is(":checked")).trigger("change");
    };

    /**
     * Adjust the calendar size based on the current viewport.
     */
    this.adjust_calendar_size = function () {
        var calendar = $("#calendar");

        calendar.fullCalendar("option", "height", $(window).height() - 70);

        // The comparison operators here are intentionally vague, as they check for both null and undefined
        if ($(document).width() < 768 && self.last_view === null) {
            if (calendar.fullCalendar("getView").name !== "agendaDay" && calendar.fullCalendar("getView").name !== "list") {
                self.last_view = calendar.fullCalendar("getView").name;
                calendar.fullCalendar("changeView", "agendaDay");
            }
        } else if ($(document).width() >= 768 && self.last_view !== null) {
            calendar.fullCalendar("changeView", self.last_view);
            self.last_view = null;
        }
    };

    /**
     * Refresh the filters based on the current filter selection.
     */
    this.refresh_filters = function (refetch) {
        refetch = typeof refetch === "undefined" ? true : refetch;

        var categories = $("[id^='calendar-filter-category-']"), calendar_search = $("#calendar-search").val(), course_ids = "", calendar_ids = "", category_names = "";

        // Whether or not to filter by a search string
        Cookies.set("filter_search_string", calendar_search, {path: "/"});
        self.last_search_string = calendar_search;

        // Whether or not to filter by assignments, events, or both
        Cookies.set("filter_show_homework", (!$("#calendar-filter-homework").children().find("input").prop("checked") && !$("#calendar-filter-events").children().find("input").prop("checked") && !$("#calendar-filter-class").children().find("input").prop("checked") && !$("#calendar-filter-external").children().find("input").prop("checked")) || $("#calendar-filter-homework").children().find("input").prop("checked"), {path: "/"});
        Cookies.set("filter_show_events", (!$("#calendar-filter-homework").children().find("input").prop("checked") && !$("#calendar-filter-events").children().find("input").prop("checked") && !$("#calendar-filter-class").children().find("input").prop("checked") && !$("#calendar-filter-external").children().find("input").prop("checked")) || $("#calendar-filter-events").children().find("input").prop("checked"), {path: "/"});
        Cookies.set("filter_show_class", (!$("#calendar-filter-homework").children().find("input").prop("checked") && !$("#calendar-filter-events").children().find("input").prop("checked") && !$("#calendar-filter-class").children().find("input").prop("checked") && !$("#calendar-filter-external").children().find("input").prop("checked")) || $("#calendar-filter-class").children().find("input").prop("checked"), {path: "/"});
        Cookies.set("filter_show_external", (!$("#calendar-filter-homework").children().find("input").prop("checked") && !$("#calendar-filter-events").children().find("input").prop("checked") && !$("#calendar-filter-class").children().find("input").prop("checked") && !$("#calendar-filter-external").children().find("input").prop("checked")) || $("#calendar-filter-external").children().find("input").prop("checked"), {path: "/"});

        // Check if we should filter by selected categories
        $.each(categories, function () {
            if ($(this).children().find("input").prop("checked")) {
                category_names += ($(this).attr("id").split("calendar-filter-category-")[1] + ",");
            }
        });
        if (category_names.match(/,$/)) {
            category_names = category_names.substring(0, category_names.length - 1);
        }
        Cookies.set("filter_categories", category_names, {path: "/"});

        // If neither OR both complete/incomplete checkboxes are checked, we're not filtering by completion
        if ((!$("#calendar-filter-complete").children().find("input").prop("checked") && !$("#calendar-filter-incomplete").children().find("input").prop("checked")) || (($("#calendar-filter-complete").children().find("input").prop("checked") && $("#calendar-filter-incomplete").children().find("input").prop("checked")))) {
            Cookies.remove("filter_complete", {path: "/"});
        } else {
            // If one of the complete/incomplete checkbox was checked, just take the status of the complete checkbox since we only need a true/false value
            Cookies.set("filter_complete", $("#calendar-filter-complete").children().find("input").prop("checked"), {path: "/"});
        }

        // If we should filter by overdue elements
        if ($("#calendar-filter-overdue").children().find("input").prop("checked")) {
            Cookies.set("filter_overdue", $("#calendar-filter-overdue").children().find("input").prop("checked"), {path: "/"});
        } else {
            Cookies.remove("filter_overdue", {path: "/"});
        }

        // If all filters are off, clear the filter title
        if (calendar_ids === "" && course_ids === "" && category_names === "" && !$("#calendar-filter-complete").children().find("input").prop("checked") && !$("#calendar-filter-incomplete").children().find("input").prop("checked") && !$("#calendar-filter-overdue").children().find("input").prop("checked") && !$("#calendar-filter-homework").children().find("input").prop("checked") && !$("#calendar-filter-events").children().find("input").prop("checked") && !$("#calendar-filter-class").children().find("input").prop("checked") && !$("#calendar-filter-external").children().find("input").prop("checked")) {
            $("#filter-button-title").html("Filter");
        }

        if (refetch) {
            $("#calendar").fullCalendar("refetchEvents");
        }
    };

    /**
     * Refresh the classes based on the current filter selection.
     */
    this.refresh_classes = function (refetch) {
        refetch = typeof refetch === "undefined" ? true : refetch;

        var courses = $("[id^='calendar-filter-course-']"), course_ids = "";

        // Check if we should filter by selected courses
        $.each(courses, function () {
            if ($(this).children().find("input").prop("checked")) {
                course_ids += ($(this).attr("id").split("calendar-filter-course-")[1] + ",");
            }
        });
        if (course_ids.match(/,$/)) {
            course_ids = course_ids.substring(0, course_ids.length - 1);
        }
        Cookies.set("filter_courses_" + helium.USER_PREFS.id, course_ids, {path: "/"});

        if (refetch) {
            $("#calendar").fullCalendar("refetchEvents");
        }
    };

    this.get_calendar_item_title = function (calendar_item) {
        if (calendar_item.calendar_item_type === 1) {
            var title = (calendar_item.completed ? "<strike>" : "") + calendar_item.title + (calendar_item.completed ? "</strike>" : "");
            title = '<input id="calendar-homework-checkbox-' + calendar_item.id + '" type="checkbox" class="ace calendar-homework-checkbox"' + (calendar_item.completed ? ' checked="checked"' : '') + '"><span class="lbl" style="margin-top: -3px;"></span>' + title;

            return title;
        } else {
            return calendar_item.title;
        }
    };

    this.refresh_calendar_items = function (start, end, timezone, callback) {
        self.loading_div.spin(helium.SMALL_LOADING_OPTS);

        var events = [];

        // TODO: after the open source migration, filtering should rely on the backend (which already supports this)
        // for greatly improved efficiency

        if (Cookies.get("filter_show_external") === undefined || Cookies.get("filter_show_external") === "true") {
            helium.planner_api.get_external_calendars(function (external_calendars) {
                $.each(external_calendars, function (index, external_calendar) {
                    helium.calendar.ajax_calls.push(helium.planner_api.get_external_calendar_feed(function (data) {
                        $.each(data, function (i, calendar_item) {
                            if (Cookies.get("filter_search_string") === undefined || calendar_item.title.toLowerCase().indexOf(Cookies.get("filter_search_string")) !== -1) {
                                events.push({
                                    id: "ext_" + external_calendar.id + "_" + calendar_item.id,
                                    color: external_calendar.color,
                                    title: helium.calendar.get_calendar_item_title(calendar_item),
                                    title_no_format: calendar_item.title,
                                    start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                                    end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                                    allDay: calendar_item.all_day,
                                    editable: false,
                                    // The following elements are for list view display accuracy
                                    materials: [],
                                    show_end_time: !calendar_item.all_day,
                                    calendar_item_type: calendar_item.calendar_item_type,
                                    course: null,
                                    category: null,
                                    completed: false,
                                    priority: null,
                                    current_grade: null,
                                    comments: '',
                                    attachments: [],
                                    reminders: []
                                });
                            }
                        });
                    }, external_calendar.id, true, true));
                });
            }, false, true);
        }

        if (Cookies.get("filter_show_events") === undefined || Cookies.get("filter_show_events") === "true") {
            helium.calendar.ajax_calls.push(helium.planner_api.get_events(function (data) {
                $.each(data, function (i, calendar_item) {
                    if (Cookies.get("filter_search_string") === undefined ||
                        calendar_item.title.toLowerCase().indexOf(Cookies.get("filter_search_string")) !== -1 ||
                        calendar_item.comments.toLowerCase().indexOf(Cookies.get("filter_search_string")) !== -1) {
                        events.push({
                            id: "event_" + calendar_item.id,
                            color: helium.USER_PREFS.settings.events_color,
                            title: helium.calendar.get_calendar_item_title(calendar_item),
                            title_no_format: calendar_item.title,
                            start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                            end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                            allDay: calendar_item.all_day,
                            // The following elements are for list view display accuracy
                            materials: [],
                            show_end_time: calendar_item.show_end_time,
                            calendar_item_type: calendar_item.calendar_item_type,
                            course: null,
                            category: null,
                            completed: calendar_item.completed,
                            priority: calendar_item.priority,
                            current_grade: null,
                            comments: calendar_item.comments,
                            attachments: calendar_item.attachments,
                            reminders: calendar_item.reminders
                        });
                    }
                });
            }, true, false, start.toISOString() + "T00:00Z", end.toISOString() + "T00:00Z"));
        }

        if (Cookies.get("filter_show_homework") === undefined || Cookies.get("filter_show_homework") === "true") {
            helium.calendar.ajax_calls.push(helium.planner_api.get_homework_by_user(function (data) {
                $.each(data, function (i, calendar_item) {
                    var course = helium.calendar.courses[calendar_item.course];

                    if (!helium.calendar.course_groups[course.course_group].shown_on_calendar) {
                        return true;
                    }

                    // Check if any filters are applied and failing, in whic case continue before adding the item
                    if (Cookies.get("filter_search_string") !== undefined &&
                        calendar_item.title.toLowerCase().indexOf(Cookies.get("filter_search_string")) === -1 &&
                        calendar_item.comments.toLowerCase().indexOf(Cookies.get("filter_search_string")) === -1 &&
                        helium.calendar.categories[calendar_item.category].title.toLowerCase().indexOf(Cookies.get("filter_search_string")) === -1 &&
                        course.title.toLowerCase().indexOf(Cookies.get("filter_search_string")) === -1) {
                        return true;
                    }
                    if (Cookies.get("filter_complete") && Cookies.get("filter_complete") != calendar_item.completed.toString()) {
                        return true;
                    }
                    if ($.inArray(course.id.toString(), Cookies.get("filter_courses_" + helium.USER_PREFS.id).split(",")) === -1) {
                        return true;
                    }
                    var slug = helium.calendar.categories[calendar_item.category].title.replace(" ", "").toLowerCase();
                    if (Cookies.get("filter_categories") && $.inArray(slug, Cookies.get("filter_categories").split(",")) === -1) {
                        return true;
                    }
                    if (Cookies.get("filter_overdue") !== undefined && (calendar_item.completed || moment().isBefore(moment(calendar_item.start)))) {
                        return true;
                    }

                    events.push({
                        id: calendar_item.id,
                        color: course.color,
                        title: helium.calendar.get_calendar_item_title(calendar_item),
                        title_no_format: calendar_item.title,
                        start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                        end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                        allDay: calendar_item.all_day,
                        // The following elements are for list view display accuracy
                        materials: calendar_item.materials,
                        show_end_time: calendar_item.show_end_time,
                        calendar_item_type: calendar_item.calendar_item_type,
                        course: calendar_item.course,
                        category: calendar_item.category,
                        completed: calendar_item.completed,
                        priority: calendar_item.priority,
                        current_grade: calendar_item.current_grade,
                        comments: calendar_item.comments,
                        attachments: calendar_item.attachments,
                        reminders: calendar_item.reminders
                    });
                });
            }, true, false, start.toISOString() + "T00:00Z", end.toISOString() + "T00:00Z"));
        }

        if (Cookies.get("filter_show_class") === undefined || Cookies.get("filter_show_class") === "true") {
            $.each(helium.calendar.courses, function (index, course) {
                helium.calendar.ajax_calls.push(helium.planner_api.get_class_schedule_events(function (data) {
                    $.each(data, function (i, calendar_item) {
                        var course = helium.calendar.courses[calendar_item.owner_id];

                        if (!helium.calendar.course_groups[helium.calendar.courses[calendar_item.owner_id].course_group].shown_on_calendar) {
                            return true;
                        }
                        if ($.inArray(course.id.toString(), Cookies.get("filter_courses_" + helium.USER_PREFS.id).split(",")) === -1) {
                            return true;
                        }

                        if (Cookies.get("filter_search_string") === undefined || calendar_item.title.toLowerCase().indexOf(Cookies.get("filter_search_string")) !== -1) {
                            events.push({
                                id: "class_" + course.id + "_" + calendar_item.id,
                                color: course.color,
                                title: helium.calendar.get_calendar_item_title(calendar_item),
                                title_no_format: calendar_item.title,
                                start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                                end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                                allDay: calendar_item.all_day,
                                editable: false,
                                // The following elements are for list view display accuracy
                                materials: helium.calendar.get_material_ids_for_course(course),
                                show_end_time: !calendar_item.all_day,
                                calendar_item_type: calendar_item.calendar_item_type,
                                course: course.id,
                                category: null,
                                completed: false,
                                priority: null,
                                current_grade: null,
                                comments: '',
                                attachments: [],
                                reminders: []
                            });
                        }
                    });
                }, helium.calendar.courses[course.id].course_group, course.id, true, true));
            });
        }

        $.when.apply(this, helium.calendar.ajax_calls).done(function () {
            callback(events);

            self.loading_div.spin(false);
        });
    };

    /**
     * Initialize the FullCalendar plugin.
     */
    this.initialize_calendar = function () {
        helium.ajax_error_occurred = false;

        $("#calendar").fullCalendar({
            defaultTimedEventDuration: moment().hours(0).minutes(helium.USER_PREFS.settings.all_day_offset).seconds(0).format("HH:mm:ss"),
            defaultView: self.DEFAULT_VIEWS[helium.USER_PREFS.settings.default_view],
            timezone: helium.USER_PREFS.settings.time_zone,
            editable: true,
            eventClick: self.edit_calendar_item_btn,
            eventDrop: self.drop_calendar_item,
            eventResize: self.resize_calendar_item,
            nowIndicator: true,
            themeSystem: 'bootstrap3',
            eventResizeStart: function () {
                self.is_resizing_calendar_item = true;
            },
            eventResizeStop: function () {
                self.is_resizing_calendar_item = false;
            },
            eventRender: function (event, element) {
                element.find(".fc-event-title").html(event.title);

                if (event.url === undefined) {
                    var start, end = null, course_string;

                    start = moment(event.start).format(helium.HE_REMINDER_DATE_STRING);
                    // Construct a pleasant start date/time
                    if (!event.allDay) {
                        start += (" at " + moment(event.start).format(helium.HE_TIME_STRING_CLIENT));
                    }

                    // Construct a pleasant end date/time
                    if (event.end) {
                        if (event.start.clone().toDate().setHours(0, 0, 0, 0) !== event.end.clone().toDate().setHours(0, 0, 0, 0)) {
                            end = moment(event.end);
                            // If we're adding an all-day event spanning multiple days, correct the end date to be offset by one
                            if (event.allDay && !moment(event.start).isSame(end, "day")) {
                                end = end.subtract(1, "days");
                            }
                            end = " " + end.format(helium.HE_REMINDER_DATE_STRING);
                        }
                        if (!event.allDay) {
                            if (end === null) {
                                end = "";
                            }
                            end += (" " + moment(event.end).format(helium.HE_TIME_STRING_CLIENT));
                        }
                    }

                    course_string = event.calendar_item_type === 1 || event.calendar_item_type === 3 ? ((helium.calendar.courses[event.course].website.replace(/\s/g, "").length > 0 ? "<a target=\"_blank\" href=\"" + helium.calendar.courses[event.course].website + "\">" : "") + helium.calendar.courses[event.course].title + (helium.calendar.courses[event.course].website.replace(/\s/g, "").length > 0 ? "</a>" : "")) : "";
                    element.qtip({
                        content: {
                            title: "<strong>" + event.title_no_format + "</strong> on " + start,
                            text: "<div class=\"row\"><div class=\"col-xs-12\"><strong>When:</strong> " + start + (
                                event.show_end_time && end ? (" to " + end) : ""
                            ) + "</div></div>" + (
                                event.calendar_item_type === 1 || event.calendar_item_type === 3 ? "<div class=\"row\"><div class=\"col-xs-12\"><strong>Class Info:</strong> " + (
                                    event.category !== null && helium.calendar.categories[event.category].title !== "Uncategorized" ? ("<span style=\"color: " + helium.calendar.categories[event.category].color + "\">" + helium.calendar.categories[event.category].title + "</span> for ") : ""
                                ) + course_string + (
                                    !helium.calendar.courses[event.course].is_online && helium.calendar.courses[event.course].room.replace(/\s/g, "").length > 0 ? " in " + helium.calendar.courses[event.course].room : ""
                                ) + "</div></div>" : ""
                            ) + (
                                event.materials.length > 0 && helium.calendar.get_materials_from_ids(event.materials) ? "<div class=\"row\"><div class=\"col-xs-12\"><strong>Materials:</strong> " + helium.calendar.get_materials_from_ids(event.materials) + "</div></div>" : ""
                            ) + (
                                event.calendar_item_type === 1 && event.completed && event.current_grade !== "-1/100" ? "<div class=\"row\"><div class=\"col-xs-12\"><strong>Grade:</strong> " + helium.grade_for_display(event.current_grade) + "</div></div>" : ""
                            ) + (
                                event.comments.replace(/\s/g, "").length > 0 ? "<div class=\"row\"><div class=\"col-xs-12\"><strong>Comments:</strong> " + helium.get_comments_with_link(event.comments) + "</div></div>" : ""
                            ) + (
                                event.attachments.length > 0 ? "<div class=\"row\"><div class=\"col-xs-12\"><strong>Attachments:</strong> " + helium.calendar.get_attachments_from_data(event.attachments) + "</div></div>" : "")
                        },
                        hide: {
                            event: "mousedown mouseup mouseleave",
                            fixed: true,
                            delay: self.QTIP_HIDE_INTERVAL
                        },
                        position: {
                            my: "top center",
                            at: "bottom right",
                            adjust: {x: -20, resize: false}
                        },
                        show: {
                            solo: true,
                            delay: self.QTIP_SHOW_INTERVAL
                        },
                        style: {classes: "qtip-bootstrap"}
                    });
                }
            },
            firstDay: helium.USER_PREFS.settings.week_starts_on,
            header: {
                left: "today prev,next title",
                right: self.DEFAULT_VIEWS.toString()
            },
            lang: 'en',
            loading: function (loading, view) {
                if (self.loading_div) {
                    if (loading) {
                        self.loading_div.spin(helium.SMALL_LOADING_OPTS);
                    } else {
                        self.loading_div.spin(false);
                    }
                }
            },
            nextDayThreshold: "00:00:00",
            selectable: true,
            selectHelper: true,
            select: self.add_calendar_item_btn,
            titleFormat: {
                month: "MMMM YYYY",
                week: "MMM D YYYY",
                day: "ddd, MMM D, YYYY"
            }
        });

        self.last_good_date = moment("12:00 PM", "HH:mm A");
        self.last_good_end_date = self.last_good_date.clone();
        self.last_good_end_date.add(helium.USER_PREFS.settings.all_day_offset, "minutes");

        // Customize the calendar header
        $(".fc-header-right").prepend("<div class=\"btn-group\" id=\"calendar-filters\"><button data-toggle=\"dropdown\" class=\"btn btn-sm dropdown-toggle\"><span id=\"filter-button-title\">Filter</span><span class=\"icon-caret-down icon-on-right\"></span></button><ul id=\"calendar-filter-list\" class=\"dropdown-menu dropdown-menu-form pull-right\" role=\"menu\"><li id=\"filter-clear\"><a class=\"cursor-hover\">Clear Filters</a></li></ul></div>");
        $(".fc-header-right").prepend("<div class=\"btn-group\" id=\"calendar-classes\"><button data-toggle=\"dropdown\" class=\"btn btn-sm dropdown-toggle\"><span id=\"classes-button-title\">Classes</span><span class=\"icon-caret-down icon-on-right\"></span></button><ul id=\"calendar-classes-list\" class=\"dropdown-menu dropdown-menu-form pull-right\" role=\"menu\"></ul></div>");
        $(".fc-header-right").append("<span class=\"input-icon\" id=\"search-bar\"><input type=\"text\" placeholder=\"Search ...\" class=\"input-sm search-query\" id=\"calendar-search\" autocomplete=\"off\" /><i class=\"icon-search nav-search-icon\"></i></span>");
        $(".fc-header-space, .fc-button").addClass("hidden-print");
        $(".fc-header-right").addClass("hidden-print");
        $(".fc-button-month, .fc-button-agendaWeek, #calendar-filters, #search-bar").addClass("hidden-xs");
        $("#loading-calendar").spin(false);
        self.loading_div = $(".fc-header-left").append("<div id=\"fullcalendar-loading\" class=\"loading-mini\" style=\"padding-left: 25px; padding-top: 2px;\"><div id=\"loading-fullcalendar\"></div></div>").find("#loading-fullcalendar");

        self.ajax_calls.push(helium.planner_api.get_courses(function (data) {
            if (helium.data_has_err_msg(data)) {
                helium.ajax_error_occurred = true;
                self.loading_div.spin(false);

                bootbox.alert(helium.get_error_msg(data));
            } else {
                var course_ids = [];
                $.each(data, function (index, course) {
                    if (!helium.calendar.courses.hasOwnProperty(course.id)) {
                        course_ids.push(course.id);
                        helium.calendar.courses[course.id] = course;

                        if (!helium.calendar.course_groups[course.course_group].shown_on_calendar) {
                            return true;
                        }

                        $("#homework-class").append("<option value=\"" + course.id + "\">" + course.title + "</option>");
                    }
                });

                if (Cookies.get("filter_courses_" + helium.USER_PREFS.id) === undefined) {
                    Cookies.set("filter_courses_" + helium.USER_PREFS.id, course_ids.join(","), {path: "/"});
                }

                $("#calendar").fullCalendar("addEventSource", self.refresh_calendar_items);

                $("#homework-class").chosen({
                    width: "100%",
                    search_contains: true,
                    no_results_text: "No classes match"
                });

                self.adjust_calendar_size();

                // If the course array is empty
                if (data.length === 0) {
                    //$("#homework-event-switch").prop("checked", true).trigger("change");
                }

                // Throw up the Getting Started modal if necessary
                if (helium.USER_PREFS.settings.show_getting_started) {
                    $("#getting-started-modal").modal("show");
                }

                self.initialize_filters(data);
                self.initialize_search_bindings();

                $("#filter-clear").on("click", function () {
                    $("#filter-button-title").html("Filter");
                    $.each($("[id^='calendar-filter-category-'], #calendar-filter-homework, #calendar-filter-events, #calendar-filter-class, #calendar-filter-external, #calendar-filter-complete, #calendar-filter-incomplete, #calendar-filter-overdue"), function () {
                        $(this).children().find("input").prop("checked", false);
                    });
                    self.refresh_filters();
                });

                $(".dropdown-menu").on("click", function (e) {
                    if ($(this).hasClass("dropdown-menu-form")) {
                        e.stopPropagation();
                    }
                });
            }
        }, true, true));
    };

    /**
     * Initialize bindings for the search form.
     */
    this.initialize_search_bindings = function () {
        $("#calendar-search").keyup(function () {
            if ($("#calendar-search").val() !== self.last_search_string) {
                clearTimeout(self.typing_timer);
                self.typing_timer = setTimeout(function () {
                    self.refresh_filters(false);
                    self.refresh_classes();
                }, self.DONE_TYPING_INTERVAL);
            }
        });

        $("#calendar-search").keydown(function () {
            clearTimeout(self.typing_timer);
        });
    };

    /**
     * Stop propogation of an event.
     */
    this.event_stop_propagation = function (e) {
        e.stopPropagation();
    };

    /**
     * Updated filter checkboxes with the change of this.
     */
    this.update_filter_checkbox_from_event = function () {
        self.update_filter_checkbox($(this));
    };

    this.get_material_styled_titles_from_data = function (data) {
        var titles = "";

        $.each(data, function (index, id) {
            titles += '<span class="label label-info arrowed-right" style="padding-top: 2px;">' + helium.calendar.materials[id].title + "</span>&nbsp;";
        });

        return titles;
    };

    this.get_attachments_from_data = function (data) {
        var titles = "";

        $.each(data, function (index, item) {
            titles += '<a href="' + item.attachment + '" download>' + item.title + '</a>&nbsp;';
        });

        return titles;
    };

    this.get_materials_from_ids = function (data) {
        var titles = [];

        $.each(data, function (index, id) {
            titles.push(helium.calendar.materials[id].title);
        });

        return titles.join(", ");
    };

    this.get_material_ids_for_course = function (course) {
        var ids = [];

        $.each(helium.calendar.materials, function (index, material) {
            if ($.inArray(course.id, material.courses)) {
                ids.push(material.id);
            }
        });

        return ids;
    };

    /**
     * Initialize the filters.
     *
     * @param courses the courses to be included in the filter
     */
    this.initialize_filters = function (courses) {
        var i = 0, loading_filters;

        loading_filters = $("#calendar-filter-list").prepend("<div id=\"filters-loading\" class=\"loading-inline pull-left\"><div id=\"loading-filters\"></div></div>").find("#loading-filters");
        loading_filters.spin(helium.FILTER_LOADING_OPTS);
        $("#calendar-filter-list").append("<li class=\"divider\"></li><li id=\"calendar-filter-homework\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\"/> &nbsp;<span>Assignments</span></a></li><li id=\"calendar-filter-events\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\"/> &nbsp;<span>Events</span></a></li><li id=\"calendar-filter-class\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\"/> &nbsp;<span>Class Schedule</span></a></li><li id=\"calendar-filter-external\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\"/> &nbsp;<span>External Calendar</span></a></li><li class=\"divider\"></li><li id=\"calendar-filter-complete\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\"/> &nbsp;<span>Complete</span></a></li><li id=\"calendar-filter-incomplete\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\" /> &nbsp;<span>Incomplete</span></a></li><li id=\"calendar-filter-overdue\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\" /> &nbsp;<span>Overdue</span></a></li>");
        $("#calendar-filter-homework input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-homework a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-events input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-events a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-class input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-class a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-external input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-external a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-complete input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-complete a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-incomplete input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-incomplete a").on("click", self.update_filter_checkbox_from_event);
        $("#calendar-filter-overdue input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
        $("#calendar-filter-overdue a").on("click", self.update_filter_checkbox_from_event);

        // Initialize course filters
        var course_ids = Cookies.get("filter_courses_" + helium.USER_PREFS.id).split(",");
        var courses_added = 0;
        if (courses.length > 0) {
            for (i = 0; i < courses.length; i += 1) {
                if (!helium.calendar.course_groups[courses[i].course_group].shown_on_calendar) {
                    continue;
                }

                $("#calendar-classes-list").append("<li id=\"calendar-filter-course-" + courses[i].id + "\"><a class=\"checkbox cursor-hover filter-course-title\"><input type=\"checkbox\" " + ($.inArray(courses[i].id.toString(), course_ids) !== -1 ? "checked=\"checked\"" : "") + "/> &nbsp;<span style=\"color: " + courses[i].color + "\">" + courses[i].title + "</span></a></li>");
                $("#calendar-filter-course-" + courses[i].id + " input").on("click", self.event_stop_propagation).on("change", self.refresh_classes);
                $("#calendar-filter-course-" + courses[i].id + " a").on("click", function () {
                    var checkbox;
                    checkbox = $($(this).children()[0]);
                    checkbox.prop("checked", !checkbox.is(":checked")).trigger("change");
                });

                courses_added += 1;
            }
        }

        if (courses_added == 0) {
            $("#calendar-classes button").attr("disabled", "disabled");
            $("#calendar-filters button").attr("disabled", "disabled");
        }

        if ($("[id^='calendar-classes-course-']").length === 0) {
            $("#create-homework").attr("disabled", "disabled");
        } else {
            $("#create-homework").removeAttr("disabled");
        }

        if (!helium.ajax_error_occurred) {
            // Initialize category filters
            helium.planner_api.get_category_names(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    self.loading_div.spin(false);
                    loading_filters.spin(false);

                    bootbox.alert(helium.get_error_msg(data));
                } else {
                    var categories = [];
                    $("#calendar-filter-list").append("<div class=\"filter-strike\"><span>Categories</span></div>");
                    for (i = 0; i < data.length; i += 1) {
                        var slug = data[i].title.replace(" ", "").toLowerCase();
                        if ($.inArray(slug, categories) === -1) {
                            categories.push(slug);
                            $("#calendar-filter-list").append("<li id=\"calendar-filter-category-" + slug + "\"><a class=\"checkbox cursor-hover\"><input type=\"checkbox\" /> &nbsp;<span>" + data[i].title + "</span></a></li>");
                            $("#calendar-filter-category-" + slug + " input").on("click", self.event_stop_propagation).on("change", self.refresh_filters);
                            $("#calendar-filter-category-" + slug + " a").on("click", self.update_filter_checkbox_from_event);
                        }
                    }

                    loading_filters.spin(false);
                }
            });
        }
    };

    /**
     * Delete the given homework ID.
     *
     * @param event the ID of the homework to delete.
     */
    this.delete_calendar_item = function (event) {
        helium.ajax_error_occurred = false;

        $("#loading-homework-modal").spin(helium.SMALL_LOADING_OPTS);

        var callback = function (data) {
            if (helium.data_has_err_msg(data)) {
                helium.ajax_error_occurred = true;
                $("#loading-homework-modal").spin(false);

                $("#homework-error").html(helium.get_error_msg(data));
                $("#homework-error").parent().show("fast");
            } else {
                $("#calendar").fullCalendar("removeEvents", self.current_calendar_item.id);
                $("#calendar").fullCalendar("refresh");
                $("#calendar").fullCalendar("unselect");

                self.nullify_calendar_item_persistence();

                $("#loading-homework-modal").spin(false);
                self.loading_div.spin(false);
                $("#homework-modal").modal("hide");
            }
        };
        if (event.calendar_item_type === 0) {
            helium.planner_api.delete_event(callback, event.id);
        } else {
            var course = helium.calendar.courses[event.course];

            helium.planner_api.delete_homework(callback, course.course_group, course.id, event.id);
        }
    };

    /**
     * Clone the given homework ID.
     *
     * @param event the ID of the homework to clone.
     */
    this.clone_calendar_item = function (event) {
        helium.ajax_error_occurred = false;

        $("#loading-homework-modal").spin(helium.SMALL_LOADING_OPTS);

        var callback = function (data) {
            if (helium.data_has_err_msg(data)) {
                helium.ajax_error_occurred = true;
                $("#loading-homework-modal").spin(false);

                $("#homework-error").html(helium.get_error_msg(data));
                $("#homework-error").parent().show("fast");
            } else {
                var calendar_item = data, event;
                calendar_item.id = calendar_item.calendar_item_type === 0 ? "event_" + calendar_item.id : calendar_item.id;

                $("#calendar").fullCalendar("renderEvent", {
                    id: calendar_item.id,
                    color: calendar_item.calendar_item_type === 1 ? helium.calendar.courses[calendar_item.course].color : helium.USER_PREFS.settings.events_color,
                    title: helium.calendar.get_calendar_item_title(calendar_item),
                    title_no_format: calendar_item.title,
                    start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                    end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                    allDay: calendar_item.all_day,
                    // The following elements are for list view display accuracy
                    materials: calendar_item.calendar_item_type === 1 ? calendar_item.materials : [],
                    show_end_time: calendar_item.show_end_time,
                    calendar_item_type: calendar_item.calendar_item_type,
                    course: calendar_item.calendar_item_type === 1 ? calendar_item.course : null,
                    category: calendar_item.calendar_item_type === 1 ? calendar_item.category : null,
                    completed: calendar_item.calendar_item_type === 1 ? calendar_item.completed : false,
                    priority: calendar_item.priority,
                    current_grade: calendar_item.calendar_item_type === 1 ? calendar_item.current_grade : null,
                    comments: calendar_item.comments,
                    attachments: calendar_item.attachments,
                    reminders: calendar_item.reminders
                });
                event = $("#calendar").fullCalendar("clientEvents", [calendar_item.id])[0];

                self.edit = false;
                self.edit_calendar_item_btn(event);
            }
        };
        var cloned = $.extend({}, self.current_calendar_item);

        delete cloned["attachments"];
        delete cloned["materials"];
        delete cloned["reminders"];
        delete cloned["source"];

        cloned["title"] = $("#homework-title").val() + " (Cloned)";
        cloned["start"] = moment(cloned.start.format()).format();
        cloned["end"] = moment(cloned.end.format()).format();
        cloned["course"] = $("#homework-class").val();
        cloned["all_day"] = cloned["allDay"];
        cloned["category"] = $("#homework-category").val() !== null ? $("#homework-category").val().toString() : "-1"
        if ($("#homework-materials").val()) {
            cloned["materials"] = $("#homework-materials").val();
        }

        if (event.calendar_item_type === 0) {
            helium.planner_api.add_event(callback, cloned);
        } else {
            var course = helium.calendar.courses[event.course];

            helium.planner_api.add_homework(callback, course.course_group, course.id, cloned);
        }
    };

    /**
     * Add the given reminder data to the reminder table.
     *
     * @param reminder the reminder data to be added
     * @param unsaved true if the reminder being added has not yet been saved to the database
     */
    this.add_reminder_to_table = function (reminder, unsaved) {
        var unsaved_string, row, i = 0, offset_type_options = "", type_options = "";
        $("#no-reminders").hide();
        unsaved_string = "";
        if (unsaved) {
            unsaved_string = "-unsaved";
            self.reminder_unsaved_pk += 1;
        }

        for (i = 0; i < helium.REMINDER_OFFSET_TYPE_CHOICES.length; i += 1) {
            offset_type_options += ("<option value=\"" + i + "\"" + (i === parseInt(reminder.offset_type) ? " selected=\"true\"" : "") + ">" + helium.REMINDER_OFFSET_TYPE_CHOICES[i] + "</option>");
        }
        for (i = 0; i < helium.REMINDER_TYPE_CHOICES.length; i += 1) {
            type_options += ("<option value=\"" + i + "\"" + (i === parseInt(reminder.type) ? " selected=\"true\"" : "") + ">" + helium.REMINDER_TYPE_CHOICES[i] + "</option>");
        }
        row = "<tr id=\"reminder-" + reminder.id + unsaved_string + "\"><td><a class=\"cursor-hover\" data-type=\"textarea\" id=\"reminder-" + reminder.id + unsaved_string + "-message\">" + reminder.message + "</a></td><td><select id=\"reminder-" + reminder.id + unsaved_string + "-type\">" + type_options + "</select> <a class=\"cursor-hover\" data-type=\"text\" id=\"reminder-" + reminder.id + unsaved_string + "-offset\">" + reminder.offset + "</a> <select id=\"reminder-" + reminder.id + unsaved_string + "-offset-type\">" + offset_type_options + "</select></td><td><div class=\"btn-group\"><button class=\"btn btn-xs btn-danger\" id=\"delete-reminder-" + reminder.id + unsaved_string + "\"><i class=\"icon-trash bigger-120\"></i></button></div></td></tr>";
        $("#reminders-table-body").append(row);

        // Bind attributes within added row
        $("#reminder-" + reminder.id + unsaved_string + "-message").editable({
            value: reminder.message,
            success: function () {
                var id = $(this).attr("id").split("reminder-")[1].split("-message")[0], parent_id = $(this).parent().parent().attr("id");
                if (id.split("-").length === 2) {
                    id = id.split("-")[1];
                }
                if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                    $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
                }
            },
            type: "textarea",
            mode: "inline"
        });
        $("#reminder-" + reminder.id + unsaved_string + "-type").on("change", function () {
            var id = $(this).attr("id").split("reminder-")[1].split("-type")[0], parent_id = $(this).parent().parent().attr("id");
            if (id.split("-").length === 2) {
                id = id.split("-")[1];
            }
            if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
            }
        });
        $("#reminder-" + reminder.id + unsaved_string + "-offset").editable({
            value: reminder.offset,
            success: function () {
                var id = $(this).attr("id").split("reminder-")[1].split("-offset")[0], parent_id = $(this).parent().parent().attr("id");
                if (id.split("-").length === 2) {
                    id = id.split("-")[1];
                }
                if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                    $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
                }
            },
            type: "text",
            tpl: '<input type="number" maxlength="5">',
            validate: function (value) {
                var response = "";
                if (!/\S/.test(value)) {
                    response = "This cannot be empty.";
                } else if (isNaN(value)) {
                    response = "This must be a number.";
                }
                return response;
            }
        });
        $("#reminder-" + reminder.id + unsaved_string + "-offset-type").on("change", function () {
            var id = $(this).attr("id").split("reminder-")[1].split("-offset-type")[0], parent_id = $(this).parent().parent().attr("id");
            if (id.split("-").length === 2) {
                id = id.split("-")[1];
            }
            if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
            }
        });

        if (unsaved) {
            $("#delete-reminder-" + reminder.id + unsaved_string).on("click", function () {
                $("#reminder-" + reminder.id + unsaved_string).hide("fast", function () {
                    $(this).remove();
                    if ($("#reminders-table-body").children().length === 1) {
                        $("#no-reminders").show();
                    }
                });
            });
        } else {
            $("#delete-reminder-" + reminder.id).on("click", function () {
                var dom_id = $(this).attr("id");
                var id = dom_id.split("-");
                id = id[id.length - 1];
                helium.calendar.reminders_to_delete.push(id);

                if ($("#reminders-table-body").children().length === 1) {
                    $("#no-reminders").show();
                }
                $("#reminder-" + reminder.id).hide("fast", function () {
                    $(this).remove();
                    if ($("#reminders-table-body").children().length === 1) {
                        $("#no-reminders").show();
                    }
                });
            });
        }
    };

    /**
     * Save changes to the calendar item.
     */
    this.save_calendar_item = function () {
        helium.ajax_error_occurred = false;

        var calendar_item_title = $("#homework-title").val(), calendar_item_start_date = $("#homework-start-date").val(), calendar_item_start_time = $("#homework-start-time").val(), moment_end_time = moment(calendar_item_start_time, helium.HE_TIME_STRING_CLIENT), calendar_item_end_time = $("#homework-end-time").is(":visible") ? $("#homework-end-time").val() : moment_end_time.add(helium.USER_PREFS.settings.all_day_offset, "minutes").format(helium.HE_TIME_STRING_CLIENT), calendar_item_end_date = $("#homework-show-end-time").is(":checked") ? $("#homework-end-date").val() : calendar_item_start_date, homework_category = $("#homework-category").val(), completed, is_category_valid, data;

        self.clear_calendar_item_errors();

        // Validate
        is_category_valid = $("#homework-category").find("option").length === 0 || homework_category !== null || (self.current_calendar_item !== null && self.current_calendar_item.calendar_item_type === 0) || $("#homework-event-switch").is(":checked");
        if (/\S/.test(calendar_item_title) && calendar_item_start_date !== "" && calendar_item_end_date !== "" && is_category_valid) {
            var reminders_data = [], id, start, end;
            $("#loading-homework-modal").spin(helium.SMALL_LOADING_OPTS);

            completed = $("#homework-completed").is(":checked");

            // Build a JSONifyable list of reminder elements
            $("[id^='reminder-'][id$='-modified']").each(function () {
                helium.planner_api.edit_reminder(function () {
                    }, $(this).attr("id").split("reminder-")[1].split("-modified")[0],
                    {
                        "title": $($(this).children()[0]).text(),
                        "message": $($(this).children()[0]).text(),
                        "type": $($(this).children()[1]).find("[id$='-type']").val(),
                        "offset": $($(this).children()[1]).find("[id$='-offset']").text(),
                        "offset_type": $($(this).children()[1]).find("[id$='-offset-type']").val()
                    });
            });

            $("[id^='reminder-'][id$='-unsaved']").each(function () {
                reminders_data.push({
                    "title": $($(this).children()[0]).text(),
                    "message": $($(this).children()[0]).text(),
                    "type": $($(this).children()[1]).find("[id$='-type']").val(),
                    "offset": $($(this).children()[1]).find("[id$='-offset']").text(),
                    "offset_type": $($(this).children()[1]).find("[id$='-offset-type']").val()
                });
            });

            // If the all-day box is checked, set times to midnight
            if ($("#homework-all-day").is(":checked")) {
                start = moment(calendar_item_start_date + " 12:00 AM", helium.HE_DATE_TIME_STRING_CLIENT);
                end = moment(calendar_item_end_date + " 12:00 AM", helium.HE_DATE_TIME_STRING_CLIENT).add(1, "days");
            } else {
                start = moment(calendar_item_start_date + " " + calendar_item_start_time, helium.HE_DATE_TIME_STRING_CLIENT);
                end = moment(calendar_item_end_date + " " + calendar_item_end_time, helium.HE_DATE_TIME_STRING_CLIENT);
            }

            // In the event that all-day was not checked, but the timed event spans multiple days, still correct for the all-day offset
            if (!$("#homework-all-day").is(":checked") && !moment(start.isSame(end, "day"))) {
                end = end.add(1, "days");
            }

            // Stringify
            start = start.toISOString();
            end = end.toISOString();

            data = {
                "title": $("#homework-title").val(),
                "all_day": $("#homework-all-day").is(":checked"),
                "show_end_time": $("#homework-show-end-time").is(":checked"),
                "start": start,
                "end": end,
                "current_grade": completed && $("#homework-grade").val() !== "" ? $("#homework-grade").val().replace(/\s/g, "") : "-1/100",
                "priority": $("#homework-priority > span").slider("option", "value"),
                "completed": completed,
                "comments": $("#homework-comments").html(),
                "course": $("#homework-class").val(),
                "category": homework_category !== null ? homework_category.toString() : "-1"
            };
            if ($("#homework-materials").val()) {
                data["materials"] = $("#homework-materials").val();
            }
            if (self.edit) {
                if (self.current_calendar_item.calendar_item_type === 1) {
                    helium.planner_api.get_courses(function (courses) {
                        data["course_group"] = helium.calendar.get_course_from_list_by_pk(courses, data["course"]).course_group;
                    }, false, true);
                }

                $.each(reminders_data, function (i, reminder_data) {
                    if (self.current_calendar_item.calendar_item_type === 1) {
                        reminder_data["homework"] = self.current_calendar_item.id;
                    } else {
                        reminder_data["event"] = self.current_calendar_item.id.substr(6);
                    }

                    helium.calendar.ajax_calls.push(helium.planner_api.add_reminder(function () {
                        if (helium.data_has_err_msg(data)) {
                            helium.ajax_error_occurred = true;
                            $("#loading-courses").spin(false);

                            $("#course-error").html(helium.get_error_msg(data));
                            $("#course-error").parent().show("fast");

                            return false;
                        }
                    }, reminder_data));
                });

                if (!helium.ajax_error_occurred) {
                    $.each(helium.calendar.reminders_to_delete, function (i, reminder_id) {
                        helium.calendar.ajax_calls.push(helium.planner_api.delete_reminder(function () {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-courses").spin(false);

                                $("#course-error").html(helium.get_error_msg(data));
                                $("#course-error").parent().show("fast");

                                return false;
                            } else {
                                var new_count = parseInt($("#reminder-bell-count").text()) - 1;
                                var popup = $("#reminder-popup-" + reminder_id);

                                if (popup.length > 0) {
                                    popup.hide();

                                    $("#reminder-bell-count").html(new_count + " Reminder" + (new_count > 1 ? "s" : ""));
                                    $("#reminder-bell-alt-count").html(new_count);
                                    if (new_count === 0) {
                                        $("#reminder-bell-alt-count").hide("fast");
                                    }
                                }
                            }
                        }, reminder_id));
                    });
                }

                if (!helium.ajax_error_occurred) {
                    $.each(helium.calendar.attachments_to_delete, function (i, attachment_id) {
                        helium.calendar.ajax_calls.push(helium.planner_api.delete_attachment(function () {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-courses").spin(false);

                                $("#course-error").html(helium.get_error_msg(data));
                                $("#course-error").parent().show("fast");

                                return false;
                            }
                        }, attachment_id));
                    });
                }

                callback = function (data) {
                    if (helium.data_has_err_msg(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-homework-modal").spin(false);

                        $("#homework-error").html(helium.get_error_msg(data));
                        $("#homework-error").parent().show("fast");
                    } else {
                        if (!helium.ajax_error_occurred) {
                            var calendar_item = data;

                            if (calendar_item.calendar_item_type === 0) {
                                calendar_item.id = "event_" + calendar_item.id;
                            }

                            calendar_item.attachments = self.current_calendar_item.attachments;

                            self.update_current_calendar_item(calendar_item);

                            self.last_type_event = $("#homework-event-switch").is(":checked");
                            self.last_good_date = moment(calendar_item.start);
                            self.last_good_end_date = moment(calendar_item.end);

                            if (self.dropzone !== null && self.dropzone.getQueuedFiles().length > 0) {
                                self.dropzone.processQueue();
                            } else {
                                self.current_calendar_item = $("#calendar").fullCalendar("clientEvents", [calendar_item.id])[0];
                                // Only update the calendar's event if the event is currently rendered on the calendar
                                if (self.current_calendar_item !== undefined) {
                                    $("#calendar").fullCalendar("updateEvent", self.current_calendar_item);
                                    $("#calendar").fullCalendar("unselect");
                                }

                                $("#loading-homework-modal").spin(false);
                                $("#homework-modal").modal("hide");
                            }
                        }
                    }
                };

                $.when.apply(this, helium.calendar.ajax_calls).done(function () {
                    helium.calendar.reminders_to_delete = [];
                    helium.calendar.attachments_to_delete = [];

                    if (self.current_calendar_item.calendar_item_type === 0) {
                        helium.planner_api.edit_event(callback, self.current_calendar_item.id, data);
                    } else {
                        var course = helium.calendar.courses[self.current_calendar_item.course];

                        helium.planner_api.edit_homework(callback, course.course_group, course.id, self.current_calendar_item.id, data);
                    }
                });
            } else {
                if (!$("#homework-event-switch").is(":checked")) {
                    helium.planner_api.get_courses(function (courses) {
                        data["course_group"] = helium.calendar.get_course_from_list_by_pk(courses, data["course"]).course_group;
                    }, false, true);
                }

                var callback = function (data) {
                    if (helium.data_has_err_msg(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-homework-modal").spin(false);

                        $("#homework-error").html(helium.get_error_msg(data));
                        $("#homework-error").parent().show("fast");
                    } else {
                        var calendar_item = data;
                        calendar_item.id = calendar_item.calendar_item_type === 0 ? "event_" + calendar_item.id : calendar_item.id;

                        $("#calendar").fullCalendar("renderEvent", {
                            id: calendar_item.id,
                            color: calendar_item.calendar_item_type === 1 ? helium.calendar.courses[calendar_item.course].color : helium.USER_PREFS.settings.events_color,
                            title: helium.calendar.get_calendar_item_title(calendar_item),
                            title_no_format: calendar_item.title,
                            start: moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone),
                            end: moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone),
                            allDay: calendar_item.all_day,
                            // The following elements are for list view display accuracy
                            materials: calendar_item.calendar_item_type === 1 ? calendar_item.materials : [],
                            show_end_time: calendar_item.show_end_time,
                            calendar_item_type: calendar_item.calendar_item_type,
                            course: calendar_item.calendar_item_type === 1 ? calendar_item.course : null,
                            category: calendar_item.calendar_item_type === 1 ? calendar_item.category : null,
                            completed: calendar_item.calendar_item_type === 1 ? calendar_item.completed : false,
                            priority: calendar_item.priority,
                            current_grade: calendar_item.calendar_item_type === 1 ? calendar_item.current_grade : null,
                            comments: calendar_item.comments,
                            attachments: calendar_item.attachments,
                            reminders: calendar_item.reminders
                        });

                        if (!helium.ajax_error_occurred) {
                            $.each(reminders_data, function (i, reminder_data) {
                                if (calendar_item.calendar_item_type === 1) {
                                    reminder_data["homework"] = calendar_item.id;
                                } else {
                                    reminder_data["event"] = calendar_item.id.substr(6);
                                }

                                helium.calendar.ajax_calls.push(helium.planner_api.add_reminder(function () {
                                    if (helium.data_has_err_msg(data)) {
                                        helium.ajax_error_occurred = true;
                                        $("#loading-courses").spin(false);

                                        $("#course-error").html(helium.get_error_msg(data));
                                        $("#course-error").parent().show("fast");

                                        return false;
                                    }
                                }, reminder_data));
                            });

                            self.last_type_event = $("#homework-event-switch").is(":checked");
                            self.last_good_date = moment(calendar_item.start);
                            self.last_good_end_date = moment(calendar_item.end);

                            if (self.dropzone !== null && self.dropzone.getQueuedFiles().length > 0) {
                                self.current_calendar_item = $("#calendar").fullCalendar("clientEvents", calendar_item.id)[0];
                                self.dropzone.processQueue();
                            } else {
                                $("#calendar").fullCalendar("unselect");

                                $("#loading-homework-modal").spin(false);
                                $("#homework-modal").modal("hide");
                            }
                        }
                    }
                };

                $.when.apply(this, helium.calendar.ajax_calls).done(function () {
                    helium.calendar.reminders_to_delete = [];
                    helium.calendar.attachments_to_delete = [];

                    if ($("#homework-event-switch").is(":checked")) {
                        helium.planner_api.add_event(function (event) {
                            helium.planner_api.get_event(callback, "event_" + event.id, false);
                        }, data);
                    } else {
                        helium.planner_api.add_homework(function (homework) {
                            helium.planner_api.get_homework(callback, data.course_group, data.course, homework.id);
                        }, data.course_group, data.course, data);
                    }
                });
            }
        } else {
            // Validation failed, so don't save and prompt the user for action
            $("#homework-error").html("You must specify values for fields highlighted in red.");
            $("#homework-error").parent().show("fast");

            if (!/\S/.test(calendar_item_title)) {
                $("#homework-title").parent().parent().addClass("has-error");
            }
            if (calendar_item_start_date === "") {
                $("#homework-start-date").parent().parent().addClass("has-error");
            }
            if (calendar_item_end_date === "") {
                $("#homework-end-date").parent().parent().addClass("has-error");
            }
            if (homework_category === null) {
                $("#homework-category").parent().parent().addClass("has-error");
            }

            $("a[href='#homework-panel-tab-1']").tab("show");
        }
    };

    /**
     * Set the timing fields with the Calendar's start, end, all_day, and set_end_time values.
     */
    this.set_timing_fields = function () {
        $("#homework-start-time").timepicker("setTime", helium.calendar.start.format(helium.HE_TIME_STRING_CLIENT));
        $("#homework-end-time").timepicker("setTime", helium.calendar.end.format(helium.HE_TIME_STRING_CLIENT));
        $("#homework-all-day").prop("checked", helium.calendar.all_day).trigger("change");
        $("#homework-show-end-time").prop("checked", helium.calendar.show_end_time).trigger("change");
    };

    /**
     * Update the current_calendar_item with the given calendar_item data from the database.
     *
     * @param calendar_item the latest calendar item from the database
     */
    this.update_current_calendar_item = function (calendar_item) {
        calendar_item.start = moment(calendar_item.start).tz(helium.USER_PREFS.settings.time_zone);
        calendar_item.end = moment(calendar_item.end).tz(helium.USER_PREFS.settings.time_zone);

        self.current_calendar_item.color = calendar_item.calendar_item_type === 1 ? helium.calendar.courses[calendar_item.course].color : helium.USER_PREFS.settings.events_color;
        self.current_calendar_item.title = helium.calendar.get_calendar_item_title(calendar_item);
        self.current_calendar_item.title_no_format = calendar_item.title;
        self.current_calendar_item.start = !calendar_item.all_day ? calendar_item.start : $("#calendar").fullCalendar("getCalendar").moment(calendar_item.start).stripTime().stripZone();
        self.current_calendar_item.end = !calendar_item.all_day ? calendar_item.end : $("#calendar").fullCalendar("getCalendar").moment(calendar_item.end).stripTime().stripZone();
        self.current_calendar_item.allDay = calendar_item.all_day;

        // The following elements are for list view display accuracy
        self.current_calendar_item.materials = calendar_item.calendar_item_type === 1 ? calendar_item.materials : [];
        self.current_calendar_item.show_end_time = calendar_item.show_end_time;
        self.current_calendar_item.course = calendar_item.calendar_item_type === 1 ? calendar_item.course : null;
        self.current_calendar_item.category = calendar_item.calendar_item_type === 1 ? calendar_item.category : null;
        self.current_calendar_item.completed = calendar_item.calendar_item_type === 1 ? calendar_item.completed : false;
        self.current_calendar_item.priority = calendar_item.priority;
        self.current_calendar_item.current_grade = calendar_item.calendar_item_type === 1 ? calendar_item.current_grade : null;
        self.current_calendar_item.comments = calendar_item.comments;
        self.current_calendar_item.attachments = calendar_item.attachments;
        self.current_calendar_item.reminders = calendar_item.reminders;

        self.current_calendar_item = $("#calendar").fullCalendar("clientEvents", [calendar_item.id])[0];
        // Only update the calendar's event if the event is currently rendered on the calendar
        if (self.current_calendar_item !== undefined) {
            $("#calendar").fullCalendar("updateEvent", self.current_calendar_item);
            $("#calendar").fullCalendar("unselect");
        }
    };
}

// Initialize HeliumClasses and give a reference to the Helium object
helium.calendar = new HeliumCalendar();

/*******************************************
 * jQuery initialization
 ******************************************/

$(document).ready(function () {
    "use strict";

    $("#loading-calendar").spin(helium.LARGE_LOADING_OPTS);

    moment.tz.setDefault(helium.USER_PREFS.settings.time_zone);

    // Prevent Dropzone auto-initialization, as we'll do it in a bit
    Dropzone.autoDiscover = false;

    $.ajax().always(function () {
        /*******************************************
         * Initialize component libraries
         ******************************************/
        // Searching is provided by the calendar page, so disable it in the dataTables library
        $.extend($.fn.dataTable.defaults, {
            "searching": false
        });
        // Add a plugin to allow ordering by checkbox
        $.fn.dataTable.ext.order['dom-checkbox'] = function (settings, col) {
            return this.api().column(col, {order: 'index'}).nodes().map(function (td, i) {
                return $('input', td).prop('checked') ? '1' : '0';
            });
        };

        bootbox.setDefaults({
            locale: 'en'
        });
        $(".date-picker").datepicker({
            autoclose: true,
            language: 'en',
            weekStart: helium.USER_PREFS.settings.week_starts_on
        }).next().on("click", function () {
            $(this).prev().focus();
        });
        $("#homework-start-date").datepicker().on("changeDate", function () {
            var start_date = moment($("#homework-start-date").val()).toDate(), end_date = moment($("#homework-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#homework-end-date").datepicker("setDate", start_date);
            }
        });
        $("#homework-end-date").datepicker().on("changeDate", function () {
            var start_date = moment($("#homework-start-date").val()).toDate(), end_date = moment($("#homework-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#homework-start-date").datepicker("setDate", end_date);
            }
        });
        $(".time-picker").timepicker({
            minuteStep: 5
        }).next().on("click", function () {
            $(this).prev().focus();
        });
        $("#homework-start-time").timepicker().on("changeTime.timepicker", function (event) {
            var start_time = moment($("#homework-start-date").val() + " " + event.time.value, helium.HE_DATE_TIME_STRING_CLIENT), end_time = moment($("#homework-end-date").val() + " " + $("#homework-end-time").val(), helium.HE_DATE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#homework-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#homework-end-time").timepicker().on("changeTime.timepicker", function (event) {
            var start_time = moment($("#homework-start-date").val() + " " + $("#homework-start-time").val(), helium.HE_DATE_TIME_STRING_CLIENT), end_time = moment($("#homework-end-date").val() + " " + event.time.value, helium.HE_DATE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#homework-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#homework-priority > span").css({width: "90%", "float": "left", margin: "15px"}).each(function () {
            var value = parseInt($(this).text(), 10);
            $(this).empty().slider({
                value: value,
                range: "min",
                animate: true
            });
        });
        $("#homework-materials").chosen({width: "100%", search_contains: true, no_results_text: "No materials match"});
        $("#homework-category").chosen({width: "100%", search_contains: true, no_results_text: "No categories match"});
        $("#homework-category").chosen().change(function () {
            $("#homework-completed").trigger("change");
        });

        /*******************************************
         * Other page initialization
         ******************************************/
        helium.calendar.clear_filter_cookies();

        helium.calendar.course_groups = {};

        helium.planner_api.get_course_groups(function (data) {
            $.each(data, function (index, course_group) {
                helium.calendar.course_groups[course_group['id']] = course_group;
            });
        }, false, true);

        helium.calendar.categories = {};

        helium.planner_api.get_category_names(function (data) {
            $.each(data, function (index, category) {
                helium.calendar.categories[category.id] = category;
            });
        }, false, true);

        helium.calendar.material_groups = {};
        helium.calendar.materials = {};

        helium.planner_api.get_material_groups(function (data) {
            $.each(data, function (index, material_group) {
                helium.calendar.material_groups[material_group['id']] = material_group;

                helium.planner_api.get_materials_by_material_group_id(function (data) {
                    $.each(data, function (index, material) {
                        helium.calendar.materials[material['id']] = material;
                    });
                }, material_group['id'], false, true);
            });
        }, false, true);

        helium.calendar.initialize_calendar();

        helium.calendar.adjust_calendar_size();

        $.when.apply(this, helium.calendar.ajax_calls).done(function () {
            $(".homework-help").popover({html: true}).data("bs.popover").tip().css("z-index", 1060);
        });

        $(".wysiwyg-editor").ace_wysiwyg({
            toolbar: [
                "bold", "italic", "underline", null, "insertunorderedlist", "insertorderedlist", null, "undo", "redo"
            ]
        }).prev().addClass("wysiwyg-style2");

        try {
            $(".dropzone").dropzone({
                maxFilesize: 10,
                addRemoveLinks: true,
                autoProcessQueue: false,
                uploadMultiple: true,
                parallelUploads: 10,
                dictDefaultMessage: "<span class=\"bigger-150 bolder\"><i class=\"icon-caret-right red\"></i> Drop files</span> to upload <span class=\"smaller-80 grey\">(or click)</span> <br /> <i class=\"upload-icon icon-cloud-upload blue icon-3x\"></i>",
                dictResponseError: "Error while uploading file!",
                previewTemplate: "<div class=\"dz-preview dz-file-preview\">\n  <div class=\"dz-details\">\n    <div class=\"dz-filename\"><span data-dz-name></span></div>\n    <div class=\"dz-size\" data-dz-size></div>\n    <img data-dz-thumbnail />\n  </div>\n  <div class=\"progress progress-small progress-striped active\"><div class=\"progress-bar progress-bar-success\" data-dz-uploadprogress></div></div>\n  <div class=\"dz-success-mark\"><span></span></div>\n  <div class=\"dz-error-mark\"><span></span></div>\n  <div class=\"dz-error-message\"><span data-dz-errormessage></span></div>\n</div>",
                init: function () {
                    helium.calendar.dropzone = this;
                    var CSRF_TOKEN = Cookies.get("csrftoken");

                    this.on("sendingmultiple", function (na, xhr, form_data) {
                        xhr.setRequestHeader("X-CSRFToken", CSRF_TOKEN);
                        if (helium.calendar.current_calendar_item.calendar_item_type === 0) {
                            form_data.append("event", helium.calendar.current_calendar_item.id.substr(6));
                        } else {
                            form_data.append("homework", helium.calendar.current_calendar_item.id);
                        }
                    });
                    this.on("successmultiple", function (files) {
                        helium.planner_api.get_attachments_for_calendar_item(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-homework-modal").spin(false);

                                $("#homework-error").html(helium.get_error_msg(data));
                                $("#homework-error").parent().show("fast");
                            } else {
                                helium.calendar.current_calendar_item.attachments = data;

                                $("#calendar").fullCalendar("updateEvent", helium.calendar.current_calendar_item);
                                $("#calendar").fullCalendar("unselect");

                                $("#loading-homework-modal").spin(false);
                                $("#homework-modal").modal("hide");
                            }
                        }, helium.calendar.current_calendar_item.id.toString(), helium.calendar.current_calendar_item.calendar_item_type);
                    });
                    this.on("errormultiple", function () {
                        $("#loading-homework-modal").spin(false);

                        if (helium.calendar.edit) {
                            if (helium.calendar.current_calendar_item.calendar_item_type === 0) {
                                $("#homework-error").html("The event is saved, but an error occurred while uploading attachments. If the error persists, <a href=\"/support\">contact support</a>.");
                            } else {
                                $("#homework-error").html("The assignment is saved, but an error occurred while uploading attachments. If the error persists, <a href=\"/support\">contact support</a>.");
                            }
                        }
                        else {
                            $("#homework-error").html("An unknown error occurred with attachments. If the error persists, <a href=\"/support\">contact support</a>.");
                        }
                        $("#homework-error").parent().show("fast");

                        $("a[href='#homework-panel-tab-3']").tab("show");

                        helium.calendar.dropzone.removeAllFiles();
                    });
                }
            });
        } catch (e) {
            helium.calendar.dropzone = null;
            bootbox.alert("Attachments are not supported in older browsers.");
        }
    });
});

$(window).resize(function () {
    "use strict";

    if (!helium.calendar.is_resizing_calendar_item) {
        helium.calendar.adjust_calendar_size();
    }
});

$("#homework-modal").scroll(function () {
    "use strict";

    $('.date-picker').datepicker('place');
});