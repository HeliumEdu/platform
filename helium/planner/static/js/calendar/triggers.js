/**
 * Copyright (c) 2017 Helium Edu.
 *
 * JavaScript functionality for triggers on the the /planner/calendar page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.0
 */

/*******************************************
 * Triggers
 ******************************************/

// Be responsible; don't clutter the global namespace
(function () {
    "use strict";

    $("body").on("mouseenter", "[id^='calendar-filter-course-']", function () {
        var element = $(this).find("span");
        element.attr("course_color", element.attr("style")).attr("style", "color: #fff !important;");
    });

    $("body").on("mouseleave", "[id^='calendar-filter-course-']", function () {
        var element = $(this).find("span");
        element.attr("style", element.attr("course_color")).attr("course_color", null);
    });

    $("body").on("click", "#create-homework", function () {
        helium.calendar.add_calendar_item_btn(helium.calendar.last_good_date, helium.calendar.last_good_end_date, null, null, 1);
    });

    $("body").on("click", "#create-event", function () {
        helium.calendar.add_calendar_item_btn(helium.calendar.last_good_date, helium.calendar.last_good_end_date, null, null, 0);
    });

    $("body").on("click", ".calendar-homework-checkbox", function () {
        helium.ajax_error_occurred = false;

        var completed = $(this).is(":checked"), homework_id = $(this).attr("id").split("calendar-homework-checkbox-")[1], data;
        helium.calendar.loading_div.spin(helium.SMALL_LOADING_OPTS);

        helium.planner_api.get_homework_by_id(function (h) {
            data = {"completed": completed};
            helium.planner_api.edit_homework(function (h_edited) {
                if (helium.data_has_err_msg(h_edited)) {
                    helium.ajax_error_occurred = true;
                    helium.calendar.loading_div.spin(false);

                    bootbox.alert(h_edited[0].err_msg);
                } else {
                    h["completed"] = completed;
                    helium.calendar.update_current_calendar_item(h);

                    helium.calendar.loading_div.spin(false);
                }
            }, h.course.course_group, h.course.id, homework_id, data);
        }, homework_id, true);
    });

    $("#homework-event-switch").on("change", function () {
        if ($(this).is(":checked")) {
            if (helium.calendar.edit) {
                $("#homework-modal-label").html("Edit Event");
            } else {
                $("#homework-modal-label").html("Add Event");
            }

            $("#homework-class-form-group").hide("fast");
            $("#homework-category-form-group").hide("fast");
            $("#homework-materials-form-group").hide("fast");
            $("#homework-completed-form-group").hide("fast");
            $("#homework-grade-form-group").hide("fast");
        } else {
            if (helium.calendar.edit) {
                $("#homework-modal-label").html("Edit Assignment");
            } else {
                $("#homework-modal-label").html("Add Assignment");
            }

            if ($("#homework-class").children().length <= 1) {
                $("#homework-class-form-group").hide("fast");
            } else {
                $("#homework-class-form-group").show("fast");
            }
            $("#homework-category-form-group").show("fast");
            $("#homework-materials-form-group").show("fast");
            $("#homework-completed-form-group").show("fast");
        }

        $("#homework-completed").trigger("change");
    });

    $("#homework-completed").on("change", function () {
        // Ensure all AJAX calls are complete before proceeding
        $.when.apply(this, helium.calendar.ajax_calls).done(function () {
            var selected;
            if ($("#homework-completed").is(":checked") && !$("#homework-event-switch").is(":checked")) {
                $("#loading-homework-modal").spin(helium.SMALL_LOADING_OPTS);

                helium.planner_api.get_courses(function (data) {
                    if (helium.data_has_err_msg(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-homework-modal").spin(false);

                        $("#homework-error").html(data[0].err_msg);
                        $("#homework-error").parent().show("fast");
                    } else {
                        // If the course for this Homework implements weighted grading, but the selected Category has no weight,
                        // a grade cannot be given
                        selected = $("#homework-category option:selected");
                        $("#homework-grade").attr("readonly", helium.calendar.get_course_from_list_by_pk(data, helium.calendar.current_class_id).has_weighted_grading && selected.length > 0 && selected.html().indexOf("(Not Graded)") !== -1);
                        $("#homework-grade-form-group").show("fast");

                        $("#loading-homework-modal").spin(false);
                    }
                }, true, true);
            } else {
                $("#homework-grade-form-group").hide("fast");
            }
        });
    });

    $("#homework-all-day").on("change", function () {
        if ($(this).is(":checked")) {
            $("#homework-time-form-group").hide("fast");
            $("#homework-show-end-time").next().text(" Show End Date");
        } else {
            $("#homework-time-form-group").show("fast");
            $("#homework-show-end-time").next().text(" Show End Date and Time");
        }
        if ($("#homework-show-end-time").is(":checked") && !$(this).is(":checked")) {
            $($("#homework-start-time").next().children()[0]).addClass("icon-long-arrow-right").removeClass("icon-time");
            $("#homework-end-time-form-group").show("fast");
        } else {
            $($("#homework-start-time").next().children()[0]).addClass("icon-time").removeClass("icon-long-arrow-right");
            $("#homework-end-time-form-group").hide("fast");
        }
    });

    $("#homework-show-end-time").on("change", function () {
        if ($(this).is(":checked")) {
            if (!helium.calendar.init_calendar_item) {
                $("#homework-end-date").datepicker("setDate", moment($("#homework-start-date").val(), helium.HE_DATE_STRING_CLIENT).toDate());
            }
            $($("#homework-start-date").next().children()[0]).addClass("icon-long-arrow-right").removeClass("icon-calendar");
            $("#homework-end-date-form-group").show("fast");
            $("#homework-all-day").trigger("change");
        } else {
            $($("#homework-start-date").next().children()[0]).addClass("icon-calendar").removeClass("icon-long-arrow-right");
            $("#homework-end-date-form-group").hide("fast");
            $("#homework-end-time-form-group").hide("fast");
            $($("#homework-start-time").next().children()[0]).addClass("icon-time").removeClass("icon-long-arrow-right");
        }
    });

    $("#homework-category").on("change", function () {
        helium.calendar.preferred_category_id = $(this).val();
        helium.calendar.preferred_category_name = helium.calendar.get_category_name_by_id(helium.calendar.preferred_category_id);
    });

    $("#homework-class").on("change", function () {
        helium.ajax_error_occurred = false;

        var course, month_view, month_or_list_view, start_time, end_time, day_of_week, on_days, i = 0, materials_callback, materials_load;
        $("#loading-homework-modal").spin(helium.SMALL_LOADING_OPTS);
        $("#homework-materials").attr("disabled", true).trigger("chosen:updated");
        $("#homework-category").attr("disabled", true).trigger("chosen:updated");
        helium.calendar.current_class_id = $("#homework-class").val();

        if (!helium.calendar.edit) {
            helium.planner_api.get_courses(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-homework-modal").spin(false);

                    $("#homework-error").html(data[0].err_msg);
                    $("#homework-error").parent().show("fast");
                } else {
                    course = helium.calendar.get_course_from_list_by_pk(data, helium.calendar.current_class_id);
                    helium.calendar.current_course_group_id = course.course_group;
                    month_view = $("#calendar").fullCalendar("getView").name === helium.calendar.DEFAULT_VIEWS[0];
                    month_or_list_view = $("#calendar").fullCalendar("getView").name === helium.calendar.DEFAULT_VIEWS[0] || $("#calendar").fullCalendar("getView").name === helium.calendar.DEFAULT_VIEWS[3];
                    if (month_view) {
                        if (helium.calendar.start.toDate().toDateString() !== helium.calendar.end.toDate().toDateString()) {
                            helium.calendar.all_day = true;
                        } else {
                            helium.calendar.all_day = false;
                        }
                    }
                    if (helium.calendar.all_day && helium.calendar.end.diff(helium.calendar.start, "days") > 1) {
                        helium.calendar.show_end_time = true;
                    }

                    if ((month_or_list_view || helium.calendar.all_day) && course.has_schedule) {
                        start_time = moment(course.sun_start_time);
                        end_time = moment(course.sun_end_time);
                        // If the course has a different schedule each day, set the start/end time according to the specified day
                        if (!course.same_time) {
                            day_of_week = helium.calendar.start.day();
                            // If this class isn't on this day of the week, we won't get a valid time, so grab the closest valid day
                            on_days = [course.sun, course.mon, course.tue, course.wed, course.thu, course.fri, course.sat];
                            if (!on_days[day_of_week]) {
                                for (i = 0; i < on_days.length; i += 1) {
                                    if (on_days[i]) {
                                        day_of_week = i;
                                        break;
                                    }
                                }
                            }

                            switch (day_of_week) {
                                case 1:
                                    start_time = moment(course.mon_start_time);
                                    end_time = moment(course.mon_end_time);
                                    break;
                                case 2:
                                    start_time = moment(course.tue_start_time);
                                    end_time = moment(course.tue_end_time);
                                    break;
                                case 3:
                                    start_time = moment(course.wed_start_time);
                                    end_time = moment(course.wed_end_time);
                                    break;
                                case 4:
                                    start_time = moment(course.thu_start_time);
                                    end_time = moment(course.thu_end_time);
                                    break;
                                case 5:
                                    start_time = moment(course.fri_start_time);
                                    end_time = moment(course.fri_end_time);
                                    break;
                                case 6:
                                    start_time = moment(course.sat_start_time);
                                    end_time = moment(course.sat_end_time);
                                    break;
                            }
                        }

                        helium.calendar.start.hour(start_time.hour());
                        helium.calendar.start.minute(start_time.minute());
                        if (!helium.calendar.all_day) {
                            helium.calendar.end.hour(end_time.hour());
                            helium.calendar.end.minute(end_time.minute());
                        } else {
                            helium.calendar.end.hour(start_time.hour());
                            helium.calendar.end.minute(start_time.minutes() + helium.USER_PREFS.settings.all_day_offset);
                        }
                    } else if ((month_view && !course.has_schedule) || helium.calendar.all_day) {
                        helium.calendar.start.hour(12);
                        helium.calendar.start.minute(0);
                        helium.calendar.end.hour(12);
                        helium.calendar.end.minute(helium.USER_PREFS.settings.all_day_offset);
                    }
                }
            }, false, true);
        } else {
            helium.planner_api.get_courses(function (data) {
                course = helium.calendar.get_course_from_list_by_pk(data, helium.calendar.current_class_id);
                helium.calendar.current_course_group_id = course.course_group;
            }, false, true);
        }

        helium.calendar.set_timing_fields();

        materials_callback = function (data) {
            if (helium.data_has_err_msg(data)) {
                helium.ajax_error_occurred = true;
                $("#loading-homework-modal").spin(false);

                $("#homework-error").html(data[0].err_msg);

                $("#homework-error").parent().show("fast");
            } else {
                $("#homework-materials").find("option").remove();
                $.each(data, function (index, material) {
                    $("#homework-materials").append("<option value=\"" + material.id + "\">" + material.title + "</option>");
                });

                $("#homework-materials").val(helium.calendar.preferred_material_ids);
                $("#homework-materials").prop("disabled", data.length === 0).trigger("chosen:updated");
            }
        };
        materials_load = helium.planner_api.get_materials_by_course_id(materials_callback, helium.calendar.current_class_id, true, true);
        // If an AJAX call was requested, add it to the list of async calls to wait on
        if (materials_load !== materials_callback) {
            helium.calendar.ajax_calls.push(materials_load);
        }
        // Wait on any AJAX responses before proceeding
        $.when.apply(this, helium.calendar.ajax_calls).done(function () {
            if (!helium.ajax_error_occurred) {
                helium.planner_api.get_categories_by_course_id(function (data) {
                    if (helium.data_has_err_msg(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-homework-modal").spin(false);

                        $("#homework-error").html(data[0].err_msg);
                        $("#homework-error").parent().show("fast");
                    } else {
                        var course, weight_tag;
                        $("#homework-category").find("option").remove();
                        $.each(data, function (index, category) {
                            helium.planner_api.get_courses(function (data) {
                                if (helium.data_has_err_msg(data)) {
                                    helium.ajax_error_occurred = true;
                                    $("#loading-homework-modal").spin(false);

                                    $("#homework-error").html(data[0].err_msg);
                                    $("#homework-error").parent().show("fast");
                                } else {
                                    course = helium.calendar.get_course_from_list_by_pk(data, helium.calendar.current_class_id);
                                    helium.calendar.current_course_group_id = course.course_group;
                                    weight_tag = ((course !== null && course.has_weighted_grading) ? (parseFloat(category.weight) !== 0 ? " (" + Math.round(category.weight * 100) / 100 + "%)" : " (Not Graded)") : "");
                                    $("#homework-category").append("<option value=\"" + category.id + "\">" + category.title + weight_tag + "</option>");
                                }
                            }, true, true);
                        });
                        if (helium.calendar.preferred_category_name === null) {
                            helium.calendar.preferred_category_name = helium.calendar.get_category_name_by_id(helium.calendar.preferred_category_id);
                            if (helium.calendar.preferred_category_name === null) {
                                helium.calendar.preferred_category_id = parseInt($("#homework-category").find("option").first().val());
                            }
                        } else {
                            helium.calendar.preferred_category_id = helium.calendar.get_category_id_by_name(helium.calendar.preferred_category_name);
                        }
                        $("#homework-category").val(helium.calendar.preferred_category_id);
                        $("#homework-category").prop("disabled", data.length === 0).trigger("chosen:updated");
                        $("#loading-homework-modal").spin(false);
                    }
                }, helium.calendar.current_course_group_id, helium.calendar.current_class_id, true, true);
            }
        });
    });

    $("#homework-modal").on("shown.bs.modal", function () {
        $("#homework-title").focus();
    });

    $("#homework-modal").on("hidden.bs.modal", function () {
        helium.calendar.nullify_calendar_item_persistence();
        $("#homework-error").parent().hide("fast");

        helium.calendar.clear_calendar_item_errors();
    });
    $("#edit-categories").on("click", function () {
        $.cookie("course_id", $("#homework-class").val(), {path: "/"});
        $.cookie("edit_categories", true, {path: "/"});
        window.location = "/planner/classes";
    });

    $("#homework-grade").on("focusout", function () {
        var value = $(this).val(), split;
        if (value !== "") {
            // Cleanup the string in the text field a bit
            value = $.trim(value);
            if (value.indexOf("/") !== -1 && value.match(/%$/)) {
                // If a ratio and a percentage exist, drop the percentage
                value = value.substring(0, value.length - 1);
            } else if (value.indexOf("/") === -1) {
                // If the value ends with a percentage, drop it
                if (value.match(/%$/)) {
                    value = value.substring(0, value.length - 1);
                }
                // Similarly, if the value didn't end with a percentage, clarify it's out of 100
                value += "/100";
            }

            split = value.split("/");
            // Last step, ensure values on both sides of the fraction are actually numbers
            if (isNaN(split[0]) || isNaN(split[1])) {
                value = helium.calendar.last_good_grade;
            } else {
                // Ensure there is no division by 0
                if (parseFloat(split[0]) === 0 && parseFloat(split[1]) === 0) {
                    value = "0/100";
                } else if (parseFloat(split[1]) === 0) {
                    value = helium.calendar.last_good_grade;
                }

                // If all is well, set this as a good grade and display
                helium.calendar.last_good_grade = value;
                helium.calendar.homework_render_percentage(helium.calendar.last_good_grade);
            }

            $(this).val(value);
        } else {
            helium.calendar.homework_render_percentage("");
        }
    });

    $("#save-homework").on("click", function () {
        helium.calendar.save_calendar_item();
    });

    $("#delete-homework").on("click", function () {
        helium.calendar.delete_calendar_item(helium.calendar.current_calendar_item);
    });

    $("#clone-homework").on("click", function () {
        helium.calendar.clone_calendar_item(helium.calendar.current_calendar_item);
    });

    $("#close-getting-started").on("click", function () {
        $("#close-getting-started").attr("disabled", "disabled");
        $("#start-adding-classes").attr("disabled", "disabled");

        if ($("#show-getting-started").is(":checked") === (helium.USER_PREFS.settings.show_getting_started)) {
            helium.planner_api.update_user_details(function (data) {
                $("#getting-started-modal").modal("hide");
            }, helium.USER_PREFS.id, {'show_getting_started': !$("#show-getting-started").is(":checked")});
        } else {
            $("#getting-started-modal").modal("hide");
        }
    });

    $("#start-adding-classes").on("click", function () {
        $("#close-getting-started").attr("disabled", "disabled");
        $("#start-adding-classes").attr("disabled", "disabled");

        if ($("#show-getting-started").is(":checked") === (helium.USER_PREFS.settings.show_getting_started)) {
            helium.planner_api.update_user_details(function (data) {
                window.location.href = "/planner/classes";
            }, helium.USER_PREFS.id, {'show_getting_started': !$("#show-getting-started").is(":checked")});
        } else {
            window.location.href = "/planner/classes";
        }
    });

    $("#create-reminder").on("click", function () {
        var data = {
            id: helium.calendar.reminder_unsaved_pk,
            message: "Reminder for " + ($.trim($("#homework-title").val()) !== "" ? $("#homework-title").val() : ($("#homework-event-switch").is(":checked") ? "New Event" : "New Assignment")),
            offset: helium.USER_PREFS.settings.default_reminder_offset,
            offset_type: helium.USER_PREFS.settings.default_reminder_offset_type,
            type: helium.USER_PREFS.settings.default_reminder_type
        };
        helium.calendar.add_reminder_to_table(data, true);
    });
}());