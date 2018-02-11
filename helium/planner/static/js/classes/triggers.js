/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript functionality for triggers on the the /planner/classes page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.3.3
 */

/*******************************************
 * Triggers
 ******************************************/

// Be responsible; don't clutter the global namespace
(function () {
    "use strict";
    $("#course-group-modal").on("shown.bs.modal", function () {
        $("#course-group-title").focus();
    });

    $("#course-modal, #course-group-modal").on("hidden.bs.modal", function () {
        helium.classes.nullify_course_persistence();
        helium.classes.nullify_course_group_persistence();
        $("#course-error, #course-group-error").parent().hide("fast");

        helium.classes.clear_course_errors();
        helium.classes.clear_course_group_errors();
    });

    // CourseGroup components
    $("#save-course-group").on("click", function () {
        helium.ajax_error_occurred = false;

        var course_group_title = $("#course-group-title").val(), course_group_start_date = $("#course-group-start-date").val(), course_group_end_date = $("#course-group-end-date").val(), data;

        helium.classes.clear_course_group_errors();

        // Validate
        if (/\S/.test(course_group_title) && course_group_start_date !== "" && course_group_end_date !== "") {
            $("#loading-course-group-modal").spin(helium.SMALL_LOADING_OPTS);

            data = {
                "title": course_group_title,
                "start_date": moment(course_group_start_date, helium.HE_DATE_STRING_CLIENT).format(helium.HE_DATE_STRING_SERVER),
                "end_date": moment(course_group_end_date, helium.HE_DATE_STRING_CLIENT).format(helium.HE_DATE_STRING_SERVER),
                "shown_on_calendar": !$("#course-group-shown-on-calendar").prop("checked")
            };
            if (helium.classes.edit) {
                helium.planner_api.edit_course_group(function (data) {
                    if (helium.data_has_err_msg(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-course-group-modal").spin(false);

                        $("#course-group-error").html(helium.get_error_msg(data));
                        $("#course-group-error").parent().show("fast");
                    } else {
                        var course_group = data;
                        $('a[href="#course-group-' + course_group.id + '"]').html("<i class=\"icon-book r-110\"></i> <span class=\"hidden-xs\">" + course_group.title + (!course_group.shown_on_calendar ? " (H)" : "") + "</span>");
                        $("#course-group-title-" + course_group.id).html(course_group.title + (!course_group.shown_on_calendar ? " (Hidden)" : ""));
                        $("#course-group-" + course_group.id + "-start-date").html(moment(course_group.start_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT));
                        $("#course-group-" + course_group.id + "-end-date").html(" to " + moment(course_group.end_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT));

                        helium.classes.refresh_course_groups();
                        helium.classes.resort_course_groups();

                        $("#loading-course-group-modal").spin(false);
                        $("#course-group-modal").modal("hide");
                    }
                }, helium.classes.edit_id, data);
            } else {
                data.average_grade = -1;

                helium.planner_api.add_course_group(helium.classes.add_course_group_to_page, data);
            }
        } else {
            // Validation failed, so don't save and prompt the user for action
            $("#course-group-error").html("You must specify values for fields highlighted in red.");
            $("#course-group-error").parent().show("fast");

            if (!/\S/.test(course_group_title)) {
                $("#course-group-title").parent().parent().addClass("has-error");
            }
            if (course_group_start_date === "") {
                $("#course-group-start-date").parent().parent().addClass("has-error");
            }
            if (course_group_end_date === "") {
                $("#course-group-end-date").parent().parent().addClass("has-error");
            }
        }
    });

    $("#create-course-group").on("click", function () {
        helium.classes.edit = false;
        $("#course-group-modal-label").html("Add Group");
        $("#course-group-title").val("");
        $("#course-group-start-date").datepicker("setDate", moment().toDate());
        $("#course-group-end-date").datepicker("setDate", moment().toDate());
        $("#course-group-shown-on-calendar").prop("checked", false);

        $("#loading-course-group-modal").spin(false);
        $("#course-group-modal").modal("show");
    });

    $("[id^='edit-course-group-']").on("click", function () {
        helium.classes.edit_course_group_btn($(this));
    });

    $("[id^='delete-course-group-']").on("click", function () {
        helium.classes.delete_course_group_btn($(this));
    });

    // Course components
    $("#course-online").on("change", function () {
        if (!$("#course-online").is(":checked")) {
            $("#course-room-form-group").show("fast");
        } else {
            $("#course-room-form-group").hide("fast");
        }
    });

    $("#course-modal").on("shown.bs.modal", function () {
        $("#course-title").focus();
    });

    $("#course-modal").on("hide.bs.modal", function () {
        $(".simplecolorpicker.picker.glyphicons").css("display", "none");
    });

    $("#course-group").on("change", function () {
        helium.ajax_error_occurred = false;

        if ($(this).val() !== "") {
            $("#loading-course-modal").spin(helium.SMALL_LOADING_OPTS);

            helium.planner_api.get_courses_by_course_group_id(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-course-modal").spin(false);

                    $("#course-error").html(helium.get_error_msg(data));
                    $("#course-error").parent().show("fast");
                } else {
                    var courses_added = [];
                    $.each(data, function (i, course) {
                        if ($.inArray(course.id, courses_added) === -1) {
                            if (!helium.classes.edit || course.id !== helium.classes.edit_id) {
                                courses_added.push(course.id);
                            }
                        }
                    });
                }
            }, $(this).val().toString());

            // If we've only selected one course group, and we're creating a new course, set the
            // start/end date for the new course to match the course group
            if (!helium.classes.edit && $(this).val().length === 1) {
                $("#course-start-date").datepicker("setDate", moment(helium.classes.course_groups[$(this).val()[0]].start_date, helium.HE_DATE_STRING_CLIENT).toDate());
                $("#course-end-date").datepicker("setDate", moment(helium.classes.course_groups[$(this).val()[0]].end_date, helium.HE_DATE_STRING_CLIENT).toDate());
            }

            $("#loading-course-modal").spin(false);
        }
    });

    $("#course-schedule-has-different-times").on("change", function () {
        if ($(this).is(":checked")) {
            $("#sun-time-lbl").html("Sunday");
            $("#sun-time-lbl-alt").html("Sunday");
            helium.classes.show_hide_schedule_times(null, false);
        } else {
            $("#sun-time-lbl").html("Time");
            $("#sun-time-lbl-alt").html("Time");
            $("#sun-time, #sun-alt-time").show("fast");
            $("#mon-time, #mon-alt-time, #tue-time, #tue-alt-time, #wed-time, #wed-alt-time, #thu-time, #thu-alt-time, #fri-time, #fri-alt-time, #sat-time, #sat-alt-time").hide("fast");
            $("#class-days-empty-palette").hide();
            $("#class-days-alt-empty-palette").hide();
        }
    });

    $("#course-schedule-has-alt-week").on("change", function () {
        if ($(this).is(":checked")) {
            $("#course-schedule-alt-week").show("fast");
            helium.classes.show_hide_schedule_times(null, false);
        } else {
            $("#course-schedule-alt-week").hide("fast");
        }
    });

    $(".course-schedule-btn").on("click", function () {
        var day = $(this).attr("id").split("course-schedule-")[1], any_shown = false;
        if ($("#course-schedule-has-different-times").is(":checked")) {
            if ($(this).hasClass("active")) {
                $("#" + day + "-time").hide("fast");
            } else {
                $("#" + day + "-time").show("fast");
                any_shown = true;
            }
        }
        helium.classes.show_hide_schedule_times(day, any_shown);
    });

    $("#course-website").on("focusout", function () {
        var value = $(this).val();
        if (value !== "") {
            if (value.indexOf("http://") !== 0 && value.indexOf("https://") !== 0) {
                value = "http://" + value;
            }
            $(this).val(value);
        }
    });

    $("#course-credits").on("focusout", function () {
        if ($(this).val() === "") {
            $(this).val("0.00");
        } else if (isNaN($(this).val())) {
            $(this).val(helium.classes.last_good_credits);
        } else {
            helium.classes.last_good_credits = $(this).val();
        }
    });

    $("#save-course").on("click", function () {
        helium.classes.save_course();
    });

    $("[id^='create-course-for-group-'], #no-classes-tab").on("click", function () {
        helium.classes.create_course_for_group_btn();
    });

    $("#create-category").on("click", function () {
        var data;
        while (!helium.classes.check_category_names("Unnamed Category" + " " + helium.classes.unnamed_category_index)) {
            helium.classes.unnamed_category_index += 1;
        }
        data = {
            id: helium.classes.category_unsaved_pk,
            title: "Unnamed Category " + helium.classes.unnamed_category_index,
            weight: 0,
            average_grade: -1,
            color: $($("#id_course_color option")[Math.floor(Math.random() * $("#id_course_color option").length)]).val(),
            course: helium.classes.edit_id
        };
        helium.classes.unnamed_category_index += 1;
        helium.classes.add_category_to_table(data, true);
    });
}());