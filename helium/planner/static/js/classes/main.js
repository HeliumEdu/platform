/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript functionality for persistence and the HeliumClasses object on the /planner/classes page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.0
 */

/**
 * Create the HeliumClasses persistence object.
 *
 * @constructor construct the HeliumClasses persistence object
 */
function HeliumClasses() {
    "use strict";

    this.CATEGORY_SUGGESTIONS = [
        {value: "Assignment", tokens: ["Assignment"]},
        {value: "Project", tokens: ["Project"]},
        {value: "Quiz", tokens: ["Quiz"]},
        {value: "Exam", tokens: ["Exam"]},
        {value: "Midterm", tokens: ["Midterm"]},
        {value: "Final Exam", tokens: ["Final Exam"]}
    ];

    this.ajax_calls = [];
    this.course_group_table = {};
    this.edit = false;
    this.edit_id = -1;
    this.course_groups = {};
    this.category_unsaved_pk = 0;
    this.last_good_credits = "0.00";
    this.unnamed_category_index = 1;
    this.dropzone = null;
    this.categories_to_delete = [];
    this.attachments_to_delete = [];

    var self = this;

    /*******************************************
     * Functions
     ******************************************/

    /**
     * Revert persistence for adding/editing a CourseGroup.
     */
    this.nullify_course_group_persistence = function () {
        self.edit = false;
        self.end = null;
        self.edit_id = -1;
        helium.ajax_error_occurred = false;
    };

    /**
     * Revert persistence for adding/editing a Course.
     */
    this.nullify_course_persistence = function () {
        self.edit = false;
        self.end = null;
        self.edit_id = -1;
        self.category_unsaved_pk = 0;
        self.last_good_credits = "0.00";
        self.unnamed_category_index = 1;
        helium.ajax_error_occurred = false;
    };

    /**
     * Clear Course marked in the Course modal.
     */
    this.clear_course_errors = function () {
        helium.ajax_error_occurred = false;
        $("#course-title").parent().parent().removeClass("has-error");
        $("#course-start-date").parent().parent().removeClass("has-error");
        $("#course-end-date").parent().parent().removeClass("has-error");
    };

    /**
     * Clear CourseGroup marked in the CourseGroup modal.
     */
    this.clear_course_group_errors = function () {
        helium.ajax_error_occurred = false;
        $("#course-group-title").parent().parent().removeClass("has-error");
        $("#course-group-start-date").parent().parent().removeClass("has-error");
        $("#course-group-end-date").parent().parent().removeClass("has-error");
    };

    /**
     * Ensure another category does not already exist with the given name.
     *
     * @param value the new value being saved for the category name
     * @return true if the name is unique, false otherwise
     */
    this.check_category_names = function (value) {
        var valid = true, id, category_id, type;
        $.each($("tr[id^='category-']"), function () {
            if (valid) {
                id = $(this).attr("id");
                category_id = id.split("-")[1];
                if (id.indexOf("modified") !== -1) {
                    id = "category-" + category_id;
                }
                type = $("#" + id + "-type").html();

                if (type === value) {
                    valid = false;
                }
            }
        });
        return valid;
    };

    /**
     * Accumulate the total weights for categories within the course to ensure they do not exceed 100%.
     *
     * @param skip_id skip the ID of the category currently being saved, as its value is given in the parameters
     * @param value the new value being saved for the skip_id
     * @return the total value of all weights
     */
    this.get_total_weights = function (skip_id, value) {
        var weight_total = 0, id, category_id, weight;
        $.each($("tr[id^='category-']"), function () {
            id = $(this).attr("id");
            category_id = id.split("-")[1];
            if (id.indexOf("modified") !== -1) {
                id = "category-" + category_id;
            }
            if (parseInt(category_id) !== skip_id) {
                weight = $("#" + id + "-weight").html();

                if (weight !== "N/A") {
                    weight_total += parseFloat(weight.substring(0, weight.length - 1), 10);
                }
            } else {
                weight_total += parseFloat(value, 10);
            }
        });

        return weight_total;
    };

    this.update_total_category_weights = function (total_weights) {
        var total_weights_row;

        if (total_weights > 0) {
            total_weights_row = $("<tr><td class=\"align-right\"></td><td></td><td></td><td></td></tr>");
            if ($("#categories-table-end-placeholder").next().length === 0) {
                $("#categories-table-end-placeholder").after(total_weights_row);
            } else {
                total_weights_row = $("#categories-table-end-placeholder").next();
            }
            $(total_weights_row.children()[0]).text("Total:");
            $(total_weights_row.children()[1]).text((Math.round(total_weights * 100) / 100) + "%");
        } else {
            $("#categories-table-end-placeholder").next().remove();
        }
    };

    /**
     * Add the given categories data to the category table.
     *
     * @param category the category data to be added
     * @param unsaved true if the category being added has not yet been saved to the database
     */
    this.add_category_to_table = function (category, unsaved) {
        var unsaved_string, row;
        $("#no-categories").hide();
        unsaved_string = "";
        if (unsaved) {
            unsaved_string = "-unsaved";
            self.category_unsaved_pk += 1;
        }

        row = "<tr id=\"category-" + category.id + unsaved_string + "\">" + "<td><a class=\"cursor-hover\" data-type=\"typeaheadjs\" id=\"category-" + category.id + unsaved_string + "-type\">" + category.title + "</a></td>" + "<td><a class=\"cursor-hover\" id=\"category-" + category.id + unsaved_string + "-weight\">" + category.weight + "</a></td>" + "<td class=\"hidden-480\">" + (category.num_homework !== undefined ? category.num_homework : "0") + "</td>" + "<td><div class=\"btn-group\"><button class=\"btn btn-xs btn-danger\" id=\"delete-category-" + category.id + unsaved_string + "\"><i class=\"icon-trash bigger-120\"></i></button></div></td>" + "</tr>";
        $("#categories-table-end-placeholder").before(row);

        // Bind attributes within added row
        $("#category-" + category.id + unsaved_string + "-type").editable({
            value: category.title,
            typeahead: {
                name: "categories",
                local: self.CATEGORY_SUGGESTIONS
            },
            success: function () {
                var id = $(this).attr("id").split("category-")[1].split("-type")[0], parent_id = $(this).parent().parent().attr("id");
                if (id.split("-").length === 2) {
                    id = id.split("-")[1];
                }
                if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                    $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
                }
            },
            type: "text",
            tpl: '<input type="text" maxlength="255">',
            validate: function (value) {
                var response = "";
                if (!/\S/.test(value)) {
                    response = "This category name cannot be empty.";
                } else if (!self.check_category_names(value)) {
                    response = "This category name already exists.";
                }
                return response;
            }
        });
        $("#category-" + category.id + unsaved_string + "-weight").editable({
            display: function (value) {
                // If no weight is given, just display N/A
                var response = "N/A";
                if (parseFloat(value) !== 0) {
                    value = helium.calculate_to_percent(value, "");
                    response = value;
                }
                $(this).html(response);
            },
            success: function () {
                var id = $(this).attr("id").split("category-")[1].split("-weight")[0], parent_id = $(this).parent().parent().attr("id");
                if (id.split("-").length === 2) {
                    id = id.split("-")[1];
                }
                if (parent_id.indexOf("unsaved") === -1 && parent_id.indexOf("modified") === -1) {
                    $(this).parent().parent().attr("id", $(this).parent().parent().attr("id") + "-modified");
                }
            },
            type: "text",
            tpl: '<input type="text" maxlength="10">',
            validate: function (value) {
                var response = "", total_weights, total_weights_row;
                // If the value is empty or set to N/A, the weight is given a value of 0
                if (!/\S/.test(value) || value === "N/A") {
                    response = {newValue: "0"};
                } else {
                    // If the value isn't already a digit, try to calculate it to one (if possible)
                    if (isNaN(value)) {
                        value = helium.calculate_to_percent(value, response).substring(0, value.length - 1);
                    }
                    total_weights = self.get_total_weights(category.id, value);
                    if (parseFloat(value) < 0) {
                        response = {newValue: "0"};
                    } else if (total_weights > 100) {
                        response = "Weights cannot total more than 100%.";
                    } else {
                        self.update_total_category_weights(total_weights);
                    }
                }
                return response;
            }
        });

        if (unsaved) {
            $("#delete-category-" + category.id + unsaved_string).on("click", function () {
                $("#category-" + category.id + unsaved_string).hide("fast", function () {
                    $(this).remove();
                    if ($("#categories-table-body").children().length === 2) {
                        $("#no-categories").show();
                    }
                });
            });
        } else {
            $("#delete-category-" + category.id).on("click", function () {
                // We can only delete this category if it is not named "Uncategorized", or if the category is empty
                if (category.num_homework > 0) {
                    if (category.title !== "Uncategorized") {
                        bootbox.dialog({
                            message: "After you save the changes to this class, all assignments attached to this category will become uncategorized.",
                            buttons: {
                                "delete": {
                                    "label": '<i class="icon-trash"></i> ' + "Delete",
                                    "className": "btn-sm btn-danger",
                                    "callback": function () {
                                        helium.classes.categories_to_delete.push(category.id);

                                        if ($("#categories-table-body").children().length === 2) {
                                            $("#no-categories").show();
                                        }
                                        $("#category-" + category.id).hide("fast", function () {
                                            $(this).remove();
                                            if ($("#categories-table-body").children().length === 2) {
                                                $("#no-categories").show();
                                            }
                                        });
                                    }
                                },
                                "cancel": {
                                    "label": '<i class="icon-remove"></i> ' + "Cancel",
                                    "className": "btn-sm"
                                }
                            }
                        });
                    } else {
                        bootbox.alert("You can't delete the \"Uncategorized\" category when there are assignments in it.");
                    }
                } else {
                    var dom_id = $(this).attr("id");
                    var id = dom_id.split("-");
                    id = id[id.length - 1];
                    if (id !== "unsaved") {
                        helium.classes.categories_to_delete.push(id);
                    }

                    $(this).remove();
                    if ($("#categories-table-body").children().length === 2) {
                        $("#no-categories").show();
                    }
                    $("#category-" + category.id).hide("fast", function () {
                        $(this).remove();
                        if ($("#categories-table-body").children().length === 2) {
                            $("#no-categories").show();
                        }
                    });
                }
            });
        }
    };

    /**
     * Create a new course in the currently open course group.
     */
    this.create_course_for_group_btn = function () {
        var i = 0, data;

        self.edit = false;
        self.categories_to_delete = [];
        self.attachments_to_delete = [];

        // First, ensure we have a material group to add the new material to
        $("#course-group").val($("#course-group-tabs li.active a").attr("href") ? $("#course-group-tabs li.active a").attr("href").split("course-group-")[1] : "");

        $("a[href='#course-panel-tab-1']").tab("show");

        $("#course-modal-label").html("Add Class");
        $("#course-title").val("");
        $("#course-start-date").datepicker("setDate", moment().toDate());
        $("#course-end-date").datepicker("setDate", moment().toDate());
        $("#course-room").val("");
        $("#course-website").val("");
        $("#course-credits").spinner("value", "0");
        $("#course-teacher-name").val("");
        $("#course-teacher-email").val("");
        $("#id_course_color").simplecolorpicker("selectColor", $($("#id_course_color option")[Math.floor(Math.random() * $("#id_course_color option").length)]).val());
        $("#course-online").prop("checked", false).trigger("change");

        // Initialize details on Schedule and Categories panels as well
        $("#course-schedule-sun").removeClass("active");
        $("#course-schedule-mon").removeClass("active");
        $("#course-schedule-tue").removeClass("active");
        $("#course-schedule-wed").removeClass("active");
        $("#course-schedule-thu").removeClass("active");
        $("#course-schedule-fri").removeClass("active");
        $("#course-schedule-sat").removeClass("active");
        $("#course-sun-start-time").timepicker("setTime", "12:00 PM");
        $("#course-sun-end-time").timepicker("setTime", "12:00 PM");
        $("#course-mon-start-time").timepicker("setTime", "12:00 PM");
        $("#course-mon-end-time").timepicker("setTime", "12:00 PM");
        $("#course-tue-start-time").timepicker("setTime", "12:00 PM");
        $("#course-tue-end-time").timepicker("setTime", "12:00 PM");
        $("#course-wed-start-time").timepicker("setTime", "12:00 PM");
        $("#course-wed-end-time").timepicker("setTime", "12:00 PM");
        $("#course-thu-start-time").timepicker("setTime", "12:00 PM");
        $("#course-thu-end-time").timepicker("setTime", "12:00 PM");
        $("#course-fri-start-time").timepicker("setTime", "12:00 PM");
        $("#course-fri-end-time").timepicker("setTime", "12:00 PM");
        $("#course-sat-start-time").timepicker("setTime", "12:00 PM");
        $("#course-sat-end-time").timepicker("setTime", "12:00 PM");
        $("#course-schedule-sun-alt").removeClass("active");
        $("#course-schedule-mon-alt").removeClass("active");
        $("#course-schedule-tue-alt").removeClass("active");
        $("#course-schedule-wed-alt").removeClass("active");
        $("#course-schedule-thu-alt").removeClass("active");
        $("#course-schedule-fri-alt").removeClass("active");
        $("#course-schedule-sat-alt").removeClass("active");
        $("#course-sun-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-sun-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-mon-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-mon-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-tue-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-tue-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-wed-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-wed-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-thu-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-thu-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-fri-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-fri-alt-end-time").timepicker("setTime", "12:00 PM");
        $("#course-sat-alt-start-time").timepicker("setTime", "12:00 PM");
        $("#course-sat-alt-end-time").timepicker("setTime", "12:00 PM");

        $("#course-schedule-has-different-times").prop("checked", false).trigger("change");
        $("#course-schedule-has-alt-week").prop("checked", false).trigger("change");

        $("tr[id^='attachment-']").remove();
        $("#no-attachments").show();
        if (self.dropzone !== null) {
            self.dropzone.removeAllFiles();
        }

        $("tr[id^='category-']").remove();
        $("#no-categories").show();

        $("#loading-course-modal").spin(false);
        $("#course-modal").modal("show");

        for (i = 0; i < self.CATEGORY_SUGGESTIONS.length; i += 1) {
            data = {
                id: self.category_unsaved_pk,
                title: self.CATEGORY_SUGGESTIONS[i].value,
                weight: 0,
                average_grade: -1,
                course: self.edit_id
            };
            self.add_category_to_table(data, true);
        }

        self.update_total_category_weights(0);
    };

    /**
     * Add the given course group's data to the page.
     *
     * @param data the data for the course group to be added
     */
    this.add_course_group_to_page = function (data) {
        if (helium.data_has_err_msg(data)) {
            helium.ajax_error_occurred = true;
            $("#loading-course-group-modal").spin(false);

            $("#course-error").html(data[0].err_msg);
            $("#course-error").parent().show("fast");
        } else {
            var input_tab, tab_date, adding_date, course_group_div, div, table_div;
            $.each($('a[href^="#course-group-"]'), function (index, tab) {
                tab_date = moment($("#course-group-" + $(tab).attr("href").split("#course-group-")[1] + "-start-date").html());
                adding_date = moment(data.start_date);
                if (!input_tab && adding_date >= tab_date) {
                    input_tab = tab;
                }
            });
            if (input_tab) {
                input_tab = $(input_tab).parent();
            } else {
                input_tab = $("#create-course-group-li");
            }
            input_tab.before("<li><a data-toggle=\"tab\" href=\"#course-group-" + data.id + "\"><i class=\"icon-book r-110\"></i> " + data.title + (!data.shown_on_calendar ? " (H)" : "") + "</a></li>");
            course_group_div = "<div id=\"course-group-" + data.id + "\" class=\"tab-pane\"><div class=\"col-sm-12\"><div class=\"table-header\"><span id=\"course-group-title-" + data.id + "\">" + data.title + (!data.shown_on_calendar ? " (Hidden)" : "") + "</span> <small class=\"hidden-xs\"><span id=\"course-group-" + data.id + "-start-date\">" + moment(data.start_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT) + "</span><span id=\"course-group-" + data.id + "-end-date\"> to " + moment(data.end_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT) + "</span></small></span><label class=\"pull-right inline action-buttons\" style=\"padding-right: 10px\"><a class=\"cursor-hover\" id=\"create-course-for-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-plus-sign-alt bigger-120 hidden-print\"></i></span></a>&nbsp;<a class=\"cursor-hover\" id=\"edit-course-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-edit bigger-120 hidden-print\"></i></span>&nbsp;</a><a class=\"cursor-hover\" id=\"delete-course-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-trash bigger-120 hidden-print\"></i></span></a></label></div><div class=\"table-responsive\"><table id=\"course-group-table-" + data.id + "\" class=\"table table-striped table-bordered table-hover\"><thead><tr><th>Title</th><th class=\"hidden-xs\">Dates</th><th>Room</th><th class=\"hidden-xs\">Teacher</th><th>Schedule</th><th class=\"hidden-xs\"></th></tr></thead><tbody id=\"course-group-table-body-" + data.id + "\"></tbody></table></div></div></div>";
            div = $("#course-group-tab-content").append(course_group_div);
            // Bind clickable attributes to their respective handlers
            div.find("#create-course-for-group-" + data.id).on("click", function () {
                self.create_course_for_group_btn();
            });
            div.find("#edit-course-group-" + data.id).on("click", function () {
                self.edit_course_group_btn($(this));
            });
            div.find("#delete-course-group-" + data.id).on("click", function () {
                self.delete_course_group_btn($(this));
            });

            table_div = div.find("#course-group-table-" + data.id).dataTable({
                aoColumns: [
                    {sWidth: "200px"},
                    {sType: "date", sClass: "hidden-xs", sWidth: "120px"},
                    null,
                    {sClass: "hidden-xs"},
                    null,
                    {sClass: "hidden-xs", bSortable: false, bSearchable: false, sWidth: "90px"}
                ],
                stateSave: true
            });
            self.course_group_table[data.id] = table_div.DataTable();
            table_div.parent().find("#course-group-table-" + data.id + "_length").addClass("hidden-print");
            table_div.parent().find("#course-group-table-" + data.id + "_filter").addClass("hidden-print");
            table_div.parent().find("#course-group-table-" + data.id + "_info").parent().parent().addClass("hidden-print");

            // Refresh the course group tags that are available
            self.refresh_course_groups();
            self.resort_course_groups();

            self.nullify_course_group_persistence();

            $("#course-group-table-" + data.id + "_filter label input").attr("placeholder", "Search ...").wrap("<span class=\"input-icon\" id=\"search-bar\">").parent().append("<i class=\"icon-search nav-search-icon\"></i>");
            $($("#course-group-table-" + data.id + "_filter label").contents()[0]).remove();

            $("#loading-course-group-modal").spin(false);
            $("#course-group-modal").modal("hide");

            $("#course-group-tabs li a[href='#course-group-" + data.id + "']").tab("show");
        }
    };

    /**
     * Resort course groups by start date.
     */
    this.resort_course_groups = function () {
        var group_tabs = $('a[href^="#course-group-"]'), swapped = true, i = 1, tab, tab_date, prev_tab, prev_tab_date, prev;
        // Good 'ol bubble sort the entries
        while (swapped) {
            swapped = false;
            for (i = 1; i < group_tabs.length; i += 1) {
                tab = group_tabs[i];
                tab_date = moment($("#course-group-" + $(tab).attr("href").split("#course-group-")[1] + "-start-date").html());
                prev_tab = group_tabs[i - 1];
                prev_tab_date = moment($("#course-group-" + $(prev_tab).attr("href").split("#course-group-")[1] + "-start-date").html());
                if (tab_date > prev_tab_date) {
                    $(prev_tab).parent().before($(tab).parent());

                    prev = group_tabs[i];
                    group_tabs[i] = group_tabs[i - 1];
                    group_tabs[i - 1] = prev;

                    swapped = true;
                }
            }
        }
    };

    /**
     * Determines whether or not to show different times for different days, both in the main time div
     * and the alt week div.
     *
     * @param day a day this course is on
     * @param any_shown if any times are shown for the standard week
     * @param any_shown_alt if any times are shown for the alt week
     */
    this.show_hide_schedule_times = function (day, any_shown, any_shown_alt) {
        if ($("#course-schedule-has-different-times").is(":checked")) {
            // Schedule times for standard week
            if ($("#course-schedule-sun").hasClass("active") && day !== "sun") {
                $("#sun-time").show("fast");
                any_shown = true;
            } else if (day !== "sun") {
                $("#sun-time").hide("fast");
            }
            if ($("#course-schedule-mon").hasClass("active") && day !== "mon") {
                $("#mon-time").show("fast");
                any_shown = true;
            } else if (day !== "mon") {
                $("#mon-time").hide("fast");
            }
            if ($("#course-schedule-tue").hasClass("active") && day !== "tue") {
                $("#tue-time").show("fast");
                any_shown = true;
            } else if (day !== "tue") {
                $("#tue-time").hide("fast");
            }
            if ($("#course-schedule-wed").hasClass("active") && day !== "wed") {
                $("#wed-time").show("fast");
                any_shown = true;
            } else if (day !== "wed") {
                $("#wed-time").hide("fast");
            }
            if ($("#course-schedule-thu").hasClass("active") && day !== "thu") {
                $("#thu-time").show("fast");
                any_shown = true;
            } else if (day !== "thu") {
                $("#thu-time").hide("fast");
            }
            if ($("#course-schedule-fri").hasClass("active") && day !== "fri") {
                $("#fri-time").show("fast");
                any_shown = true;
            } else if (day !== "fri") {
                $("#fri-time").hide("fast");
            }
            if ($("#course-schedule-sat").hasClass("active") && day !== "sat") {
                $("#sat-time").show("fast");
                any_shown = true;
            } else if (day !== "sat") {
                $("#sat-time").hide("fast");
            }

            if (any_shown) {
                $("#class-days-empty-palette").hide();
            } else {
                $("#class-days-empty-palette").show();
            }

            // Schedule times for alternate week
            if ($("#course-schedule-sun-alt").hasClass("active") && day !== "sun-alt") {
                $("#sun-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "sun-alt") {
                $("#sun-alt-time").hide("fast");
            }
            if ($("#course-schedule-mon-alt").hasClass("active") && day !== "mon-alt") {
                $("#mon-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "mon-alt") {
                $("#mon-alt-time").hide("fast");
            }
            if ($("#course-schedule-tue-alt").hasClass("active") && day !== "tue-alt") {
                $("#tue-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "tue-alt") {
                $("#tue-alt-time").hide("fast");
            }
            if ($("#course-schedule-wed-alt").hasClass("active") && day !== "wed-alt") {
                $("#wed-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "wed-alt") {
                $("#wed-alt-time").hide("fast");
            }
            if ($("#course-schedule-thu-alt").hasClass("active") && day !== "thu-alt") {
                $("#thu-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "thu-alt") {
                $("#thu-alt-time").hide("fast");
            }
            if ($("#course-schedule-fri-alt").hasClass("active") && day !== "fri-alt") {
                $("#fri-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "fri-alt") {
                $("#fri-alt-time").hide("fast");
            }
            if ($("#course-schedule-sat-alt").hasClass("active") && day !== "sat-alt") {
                $("#sat-alt-time").show("fast");
                any_shown_alt = true;
            } else if (day !== "sat-alt") {
                $("#sat-alt-time").hide("fast");
            }

            if (any_shown_alt) {
                $("#class-days-alt-empty-palette").hide();
            } else {
                $("#class-days-alt-empty-palette").show();
            }
        }
    };

    /**
     * Show the Course Group modal to edit a course group.
     *
     * @param selector the selector for the edit button of a course group
     */
    this.edit_course_group_btn = function (selector) {
        helium.ajax_error_occurred = false;

        var course_group, start_date, end_date;
        if (!self.edit) {
            $("#loading-courses").spin(helium.SMALL_LOADING_OPTS);

            self.edit = true;

            $("#course-group-modal-label").html("Edit Group");
            // Initialize dialog attributes for editing
            self.edit_id = parseInt(selector.attr("id").split("edit-course-group-")[1]);
            helium.planner_api.get_course_group(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-courses").spin(false);
                    self.edit = false;
                    self.edit_id = -1;

                    bootbox.alert(data[0].err_msg);
                } else {
                    course_group = data;
                    $("#course-group-title").val(course_group.title);
                    start_date = course_group.start_date !== null ? moment(course_group.start_date, helium.HE_DATE_STRING_SERVER).toDate() : moment().toDate();
                    end_date = course_group.end_date !== null ? moment(course_group.end_date, helium.HE_DATE_STRING_SERVER).toDate() : moment().toDate();
                    $("#course-group-start-date").datepicker("setDate", start_date);
                    $("#course-group-end-date").datepicker("setDate", end_date);
                    $("#course-group-shown-on-calendar").prop("checked", !course_group.shown_on_calendar);

                    $("#loading-course-group-modal").spin(false);
                    $("#loading-courses").spin(false);
                    $("#course-group-modal").modal("show");
                }
            }, self.edit_id);
        }
    };

    /**
     * Delete the given course group.
     *
     * @param selector the selector for the edit button of a course group
     */
    this.delete_course_group_btn = function (selector) {
        helium.ajax_error_occurred = false;

        var id = selector.attr("id").split("delete-course-group-")[1];
        bootbox.dialog({
            message: "Deleting this group will permanently delete all classes and homework associated with it.",
            buttons: {
                "delete": {
                    "label": '<i class="icon-trash"></i> Delete',
                    "className": "btn-sm btn-danger",
                    "callback": function () {
                        $("#loading-courses").spin(helium.SMALL_LOADING_OPTS);
                        helium.planner_api.delete_course_group(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-courses").spin(false);

                                bootbox.alert(data[0].err_msg);
                            } else {
                                $("#course-group-" + id).slideUp("fast", function () {
                                    var parent = $('a[href="#course-group-' + id + '"]').parent();
                                    if (parent.prev().length > 0) {
                                        parent.prev().find("a").tab("show");
                                    } else if (parent.next().length > 0 && !parent.next().is($("#create-course-group-li"))) {
                                        parent.next().find("a").tab("show");
                                    } else {
                                        $("#no-classes-tab").addClass("active");
                                    }

                                    $(this).remove();
                                    $('a[href="#course-group-' + id + '"]').parent().remove();
                                    delete self.course_groups[id];
                                    $("#loading-courses").spin(false);
                                });
                            }
                        }, id);
                    }
                },
                "cancel": {
                    "label": '<i class="icon-remove"></i> Cancel',
                    "className": "btn-sm"
                }
            }
        });
    };

    /**
     * Delete an attachment from the list of attachments.
     */
    this.delete_attachment = function (data) {
        var dom_id = $(this).attr("id");
        var id = dom_id.split("-");
        id = id[id.length - 1];
        helium.classes.attachments_to_delete.push(id);

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

    /**
     * Show the Course modal to edit a course.
     *
     * @param selector the selector for the edit button of a course
     * @param show_details true if the details panel should be shown, false otherwise
     */
    this.edit_course_btn = function (selector, show_details) {
        helium.ajax_error_occurred = false;

        var start_date, end_date, i = 0, course, total_weights = 0;
        if (!self.edit) {
            $("#loading-courses").spin(helium.SMALL_LOADING_OPTS);

            self.edit = true;
            self.categories_to_delete = [];
            self.attachments_to_delete = [];

            $("#course-modal-label").html("Edit Class");

            // Initialize dialog attributes for editing
            self.edit_id = parseInt(selector.attr("id").split("edit-course-")[1]);
            self.course_group_id = parseInt(selector.closest("[id^='course-group-table-']").attr('id').split('course-group-table-body-')[1]);
            helium.planner_api.get_course(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-courses").spin(false);
                    self.edit = false;
                    self.edit_id = -1;

                    bootbox.alert(data[0].err_msg);
                } else {
                    course = data;

                    // Change display to the correct course group tab
                    $('a[href="#course-group-' + course.course_group + '"]').tab("show");

                    if (show_details) {
                        $("a[href='#course-panel-tab-1']").tab("show");
                    }

                    $("#course-title").val(course.title);
                    if (course.start_date !== null) {
                        start_date = moment(course.start_date).toDate();
                        end_date = moment(course.end_date).toDate();
                        $("#course-start-date").datepicker("setDate", start_date);
                        $("#course-end-date").datepicker("setDate", end_date);
                    }
                    $("#course-room").val(course.room);
                    $("#course-website").val(course.website);
                    self.last_good_credits = course.credits;
                    $("#course-credits").spinner("value", self.last_good_credits);
                    $("#id_course_color").simplecolorpicker("selectColor", course.color);
                    $("#course-online").prop("checked", course.is_online);
                    $("#course-online").trigger("change");

                    $("#course-teacher-name").val(course.teacher_name);
                    $("#course-teacher-email").val(course.teacher_email);

                    $("#course-group").val(course.course_group);

                    // Initialize details on Schedule and Categories panels as well
                    if (self.on_day_of_week(course, 0)) {
                        $("#course-schedule-sun").addClass("active");
                    } else {
                        $("#course-schedule-sun").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 1)) {
                        $("#course-schedule-mon").addClass("active");
                    } else {
                        $("#course-schedule-mon").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 2)) {
                        $("#course-schedule-tue").addClass("active");
                    } else {
                        $("#course-schedule-tue").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 3)) {
                        $("#course-schedule-wed").addClass("active");
                    } else {
                        $("#course-schedule-wed").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 4)) {
                        $("#course-schedule-thu").addClass("active");
                    } else {
                        $("#course-schedule-thu").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 5)) {
                        $("#course-schedule-fri").addClass("active");
                    } else {
                        $("#course-schedule-fri").removeClass("active");
                    }
                    if (self.on_day_of_week(course, 6)) {
                        $("#course-schedule-sat").addClass("active");
                    } else {
                        $("#course-schedule-sat").removeClass("active");
                    }
                    $("#course-sun-start-time").timepicker("setTime", moment(course.sun_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sun-end-time").timepicker("setTime", moment(course.sun_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-mon-start-time").timepicker("setTime", moment(course.mon_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-mon-end-time").timepicker("setTime", moment(course.mon_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-tue-start-time").timepicker("setTime", moment(course.tue_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-tue-end-time").timepicker("setTime", moment(course.tue_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-wed-start-time").timepicker("setTime", moment(course.wed_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-wed-end-time").timepicker("setTime", moment(course.wed_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-thu-start-time").timepicker("setTime", moment(course.thu_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-thu-end-time").timepicker("setTime", moment(course.thu_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-fri-start-time").timepicker("setTime", moment(course.fri_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-fri-end-time").timepicker("setTime", moment(course.fri_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sat-start-time").timepicker("setTime", moment(course.sat_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sat-end-time").timepicker("setTime", moment(course.sat_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    if (self.on_day_of_week_alt(course, 0)) {
                        $("#course-schedule-sun-alt").addClass("active");
                    } else {
                        $("#course-schedule-sun-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 1)) {
                        $("#course-schedule-mon-alt").addClass("active");
                    } else {
                        $("#course-schedule-mon-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 2)) {
                        $("#course-schedule-tue-alt").addClass("active");
                    } else {
                        $("#course-schedule-tue-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 3)) {
                        $("#course-schedule-wed-alt").addClass("active");
                    } else {
                        $("#course-schedule-wed-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 4)) {
                        $("#course-schedule-thu-alt").addClass("active");
                    } else {
                        $("#course-schedule-thu-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 5)) {
                        $("#course-schedule-fri-alt").addClass("active");
                    } else {
                        $("#course-schedule-fri-alt").removeClass("active");
                    }
                    if (self.on_day_of_week_alt(course, 6)) {
                        $("#course-schedule-sat-alt").addClass("active");
                    } else {
                        $("#course-schedule-sat-alt").removeClass("active");
                    }
                    $("#course-sun-alt-start-time").timepicker("setTime", moment(course.sun_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sun-alt-end-time").timepicker("setTime", moment(course.sun_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-mon-alt-start-time").timepicker("setTime", moment(course.mon_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-mon-alt-end-time").timepicker("setTime", moment(course.mon_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-tue-alt-start-time").timepicker("setTime", moment(course.tue_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-tue-alt-end-time").timepicker("setTime", moment(course.tue_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-wed-alt-start-time").timepicker("setTime", moment(course.wed_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-wed-alt-end-time").timepicker("setTime", moment(course.wed_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-thu-alt-start-time").timepicker("setTime", moment(course.thu_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-thu-alt-end-time").timepicker("setTime", moment(course.thu_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-fri-alt-start-time").timepicker("setTime", moment(course.fri_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-fri-alt-end-time").timepicker("setTime", moment(course.fri_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sat-alt-start-time").timepicker("setTime", moment(course.sat_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));
                    $("#course-sat-alt-end-time").timepicker("setTime", moment(course.sat_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT));

                    $("#course-schedule-has-different-times").prop("checked", !self.same_time(course)).trigger("change");
                    $("#course-schedule-has-alt-week").prop("checked", self.has_alt_week(course)).trigger("change");

                    $("tr[id^='category-']").remove();
                    $("#no-categories").show();

                    helium.planner_api.get_categories_by_course_id(function (data) {
                        self.category_unsaved_pk = data.length + 1;
                        for (i = 0; i < data.length; i += 1) {
                            self.add_category_to_table(data[i], false);
                            total_weights += parseFloat(data[i].weight);
                        }
                    }, self.course_group_id, self.edit_id, false);

                    self.update_total_category_weights(total_weights);

                    $("tr[id^='attachment-']").remove();
                    $("#no-attachments").show();
                    if (self.dropzone !== null) {
                        self.dropzone.removeAllFiles();
                    }

                    helium.planner_api.get_attachments_by_course_id(function (data) {
                        self.attachment_unsaved_pk = data.length + 1;
                        for (i = 0; i < data.length; i += 1) {
                            $("#no-attachments").hide();

                            $("#attachments-table-body").append("<tr id=\"attachment-" + data[i].id + "\"><td>" + data[i].title + "</td><td>" + helium.bytes_to_size(parseInt(data[i].size)) + "</td><td><div class=\"btn-group\"><a target=\"_blank\" class=\"btn btn-xs btn-success\" href=\"" + data[i].attachment + "\"><i class=\"icon-cloud-download bigger-120\"></i></a> <button class=\"btn btn-xs btn-danger\" id=\"delete-attachment-" + data[i].id + "\"><i class=\"icon-trash bigger-120\"></i></button></div></td></tr>");
                            $("#delete-attachment-" + data[i].id).on("click", self.delete_attachment);
                        }
                    }, self.course_group_id, self.edit_id, false);

                    $("#loading-course-modal").spin(false);
                    $("#loading-courses").spin(false);
                    $("#course-modal").modal("show");
                }
            }, self.course_group_id, self.edit_id);
        }
    };

    /**
     * Delete the given course.
     *
     * @param selector the selector for the edit button of a course
     */
    this.delete_course_btn = function (selector) {
        helium.ajax_error_occurred = false;

        var id = selector.attr("id").split("delete-course-")[1];
        var course_group_id = parseInt(selector.closest("[id^='course-group-table-']").attr('id').split('course-group-table-body-')[1]);
        bootbox.dialog({
            message: "Deleting this class will permanently delete all homework associated with it and will remove this class from all groups.",
            buttons: {
                "delete": {
                    "label": '<i class="icon-trash"></i> Delete',
                    "className": "btn-sm btn-danger",
                    "callback": function () {
                        $("#loading-courses").spin(helium.SMALL_LOADING_OPTS);
                        self.ajax_calls.push(helium.planner_api.delete_course(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-courses").spin(false);

                                bootbox.alert(data[0].err_msg);
                            } else {
                                $("#course-" + id).slideUp("fast", function () {
                                    self.course_group_table[$("#course-group-tabs li.active a").attr("href").split("#course-group-")[1]].row($(this)).remove().draw();

                                    $("#loading-courses").spin(false);
                                });
                            }
                        }, course_group_id, id));
                    }
                },
                "cancel": {
                    "label": '<i class="icon-remove"></i> Cancel',
                    "className": "btn-sm"
                }
            }
        });
    };

    // FIXME: these course-related functions should be prototyped off a Course object after the open source migration is finished
    this.on_day_of_week = function (course, day) {
        return course.days_of_week.substring(day, day + 1) == '1';
    };

    this.on_day_of_week_alt = function (course, day) {
        return course.days_of_week_alt.substring(day, day + 1) == '1';
    };

    this.same_time = function (course) {
        return (
            (course.sun_start_time == course.mon_start_time &&
            course.sun_start_time == course.tue_start_time &&
            course.sun_start_time == course.wed_start_time &&
            course.sun_start_time == course.thu_start_time &&
            course.sun_start_time == course.fri_start_time &&
            course.sun_start_time == course.sat_start_time)
            &&
            (course.sun_end_time == course.mon_end_time &&
            course.sun_end_time == course.tue_end_time &&
            course.sun_end_time == course.wed_end_time &&
            course.sun_end_time == course.thu_end_time &&
            course.sun_end_time == course.fri_end_time &&
            course.sun_end_time == course.sat_end_time)
        )
    };

    this.has_alt_week = function (course) {
        return course.days_of_week_alt != '0000000';
    };

    this.same_time_alt = function (course) {
        return (
            (course.sun_start_time_alt == course.mon_start_time_alt &&
            course.sun_start_time_alt == course.tue_start_time_alt &&
            course.sun_start_time_alt == course.wed_start_time_alt &&
            course.sun_start_time_alt == course.thu_start_time_alt &&
            course.sun_start_time_alt == course.fri_start_time_alt &&
            course.sun_start_time_alt == course.sat_start_time_alt)
            &&
            (course.sun_end_time_alt == course.mon_end_time_alt &&
            course.sun_end_time_alt == course.tue_end_time_alt &&
            course.sun_end_time_alt == course.wed_end_time_alt &&
            course.sun_end_time_alt == course.thu_end_time_alt &&
            course.sun_end_time_alt == course.fri_end_time_alt &&
            course.sun_end_time_alt == course.sat_end_time_alt)
        )
    };

    this.has_schedule = function (course) {
        return course.days_of_week != '0000000' || course.days_of_week_alt != '0000000' || !self.same_time(course) || !self.same_time_alt(course);
    };

    this.get_schedule = function (course_data) {
        var schedule = "", schedule_alt = "", time_output = false;
        if (self.has_schedule(course_data)) {
            if (self.same_time(course_data)) {
                schedule = (self.on_day_of_week(course_data, 0) ? "<span class=\"label label-sm\">Sun</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 1) ? "<span class=\"label label-sm\">Mon</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 2) ? "<span class=\"label label-sm\">Tue</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 3) ? "<span class=\"label label-sm\">Wed</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 4) ? "<span class=\"label label-sm\">Thu</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 5) ? "<span class=\"label label-sm\">Fri</span>&nbsp;" : "") + (self.on_day_of_week(course_data, 6) ? "<span class=\"label label-sm\">Sat</span>" : "") + "<br />" + moment(course_data.sun_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sun_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT);
            } else {
                if (self.on_day_of_week(course_data, 0)) {
                    schedule = "<span class=\"label label-sm\">Sun</span><br />" + moment(course_data.sun_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sun_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT);
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 1)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\"/>";
                    }
                    schedule += ("<span class=\"label label-sm\">Mon</span><br />" + (moment(course_data.mon_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.mon_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 2)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                    }
                    schedule += ("<span class=\"label label-sm\">Tue</span><br />" + (moment(course_data.tue_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.tue_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 3)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                    }
                    schedule += ("<span class=\"label label-sm\">Wed</span><br />" + (moment(course_data.wed_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.wed_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 4)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                    }
                    schedule += ("<span class=\"label label-sm\">Thu</span><br />" + (moment(course_data.thu_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.thu_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 5)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                    }
                    schedule += ("<span class=\"label label-sm\">Fri</span><br />" + (moment(course_data.fri_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.fri_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                    time_output = true;
                }
                if (self.on_day_of_week(course_data, 6)) {
                    if (time_output) {
                        schedule += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                    }
                    schedule += ("<span class=\"label label-sm\">Sat</span><br />" + (moment(course_data.sat_start_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sat_end_time, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                }
            }

            time_output = false;
            if (self.has_alt_week(course_data)) {
                if (self.same_time_alt(course_data)) {
                    schedule_alt = (self.on_day_of_week_alt(course_data, 0) ? "<span class=\"label label-sm\">Sun</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 1) ? "<span class=\"label label-sm\">Mon</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 2) ? "<span class=\"label label-sm\">Tue</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 3) ? "<span class=\"label label-sm\">Wed</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 4) ? "<span class=\"label label-sm\">Thu</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 5) ? "<span class=\"label label-sm\">Fri</span>&nbsp;" : "") + (self.on_day_of_week_alt(course_data, 6) ? "<span class=\"label label-sm\">Sat</span>" : "") + "<br />" + moment(course_data.sun_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sun_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT);
                } else {
                    if (self.on_day_of_week_alt(course_data, 0)) {
                        schedule_alt = "<span class=\"label label-sm\">Sun</span><br />" + moment(course_data.sun_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sun_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT);
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 1)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\"/>";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Mon</span><br />" + (moment(course_data.mon_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.mon_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 2)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Tue</span><br />" + (moment(course_data.tue_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.tue_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 3)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Wed</span><br />" + (moment(course_data.wed_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.wed_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 4)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Thu</span><br />" + (moment(course_data.thu_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.thu_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 5)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Fri</span><br />" + (moment(course_data.fri_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.fri_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                    if (self.on_day_of_week_alt(course_data, 6)) {
                        if (time_output) {
                            schedule_alt += "<hr style=\"margin-top: 5px; margin-bottom: 5px\" />";
                        }
                        schedule_alt += ("<span class=\"label label-sm\">Sat</span><br />" + (moment(course_data.sat_start_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT) + " to " + moment(course_data.sat_end_time_alt, helium.HE_TIME_STRING_SERVER).format(helium.HE_TIME_STRING_CLIENT)));
                        time_output = true;
                    }
                }

                if (schedule_alt !== "") {
                    schedule_alt = "<hr style=\"margin-top: 8px; margin-bottom: 5px;\"/><b><small>Alternate</small></b><br />" + schedule_alt;
                }
            }
        }

        return schedule + schedule_alt;
    };

    /**
     * Add a course to the given course group.
     *
     * @param course_data the course data with which to build the course
     * @param table the course group table in which to add the course
     */
    this.add_course_to_groups = function (course_data, table) {
        var row = table.row.add(["<span class=\"label label-sm\" style=\"background-color: " + course_data.color + " !important\">" + (course_data.website !== "" ? "<a target=\"_blank\" href=\"" + course_data.website + "\" class=\"course-title-with-link\">" + course_data.title + " <i class=\"icon-external-link bigger-110\"></i></a>" : course_data.title) + "</span>", moment(course_data.start_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT) + " to " + moment(course_data.end_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT), course_data.room, course_data.teacher_email !== "" ? ("<a target=\"_blank\" href=\"mailto:" + course_data.teacher_email + "\" class=\"teacher-email-with-link\">" + course_data.teacher_name + "</a>") : course_data.teacher_name, self.get_schedule(course_data), "<div class=\"hidden-xs action-buttons\"><a class=\"green cursor-hover\" id=\"edit-course-" + course_data.id + "\"><i class=\"icon-edit bigger-130\"></i></a><a class=\"red cursor-hover\" id=\"delete-course-" + course_data.id + "\"><i class=\"icon-trash bigger-130\"></i></a></div>"]).node(), row_div = $(row).attr("id", "course-" + course_data.id);
        // Bind clickable attributes to their respective handlers
        row_div.find("[class$='-with-link']").on("click", function (e) {
            e.stopImmediatePropagation();
        });
        row_div.on("click", function () {
            self.edit_course_btn($(this).find("#edit-course-" + course_data.id), true);
        });
        row_div.find("#edit-course-" + course_data.id).on("click", function () {
            self.edit_course_btn($(this), true);
        });
        row_div.find("#delete-course-" + course_data.id).on("click", function (e) {
            e.stopPropagation();
            self.delete_course_btn($(this));
        });
    };

    /**
     * Initialize date/time attributes.
     */
    this.initialize_datetime = function () {
        var start_date, end_date, start_time, end_time;

        $(".date-picker").datepicker({
            autoclose: true,
            language: 'en',
            weekStart: helium.USER_PREFS.settings.week_starts_on
        }).next().on("click", function () {
            $(this).prev().focus();
        });
        $("#course-group-start-date").datepicker().on("changeDate", function () {
            start_date = moment($("#course-group-start-date").val()).toDate();
            end_date = moment($("#course-group-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#course-group-end-date").datepicker("setDate", start_date);
            }
        });
        $("#course-group-end-date").datepicker().on("changeDate", function () {
            start_date = moment($("#course-group-start-date").val()).toDate();
            end_date = moment($("#course-group-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#course-group-start-date").datepicker("setDate", end_date);
            }
        });
        $("#course-start-date").datepicker().on("changeDate", function () {
            start_date = moment($("#course-start-date").val()).toDate();
            end_date = moment($("#course-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#course-end-date").datepicker("setDate", start_date);
            }
        });
        $("#course-end-date").datepicker().on("changeDate", function () {
            start_date = moment($("#course-start-date").val()).toDate();
            end_date = moment($("#course-end-date").val()).toDate();
            if (start_date > end_date) {
                $("#course-start-date").datepicker("setDate", end_date);
            }
        });
        $(".time-picker").timepicker({
            minuteStep: 5
        }).next().on("click", function () {
            $(this).prev().focus();
        });
        $("#course-sun-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-sun-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sun-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sun-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-sun-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sun-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-mon-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-mon-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-mon-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-mon-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-mon-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-mon-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-tue-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-tue-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-tue-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-tue-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-tue-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-tue-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-wed-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-wed-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-wed-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-wed-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-wed-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-wed-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-thu-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-thu-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-thu-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-thu-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-thu-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-thu-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-fri-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-fri-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-fri-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-fri-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-fri-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-fri-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sat-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-sat-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sat-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sat-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-sat-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sat-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sun-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-sun-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sun-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sun-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-sun-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sun-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-mon-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-mon-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-mon-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-mon-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-mon-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-mon-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-tue-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-tue-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-tue-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-tue-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-tue-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-tue-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-wed-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-wed-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-wed-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-wed-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-wed-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-wed-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-thu-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-thu-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-thu-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-thu-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-thu-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-thu-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-fri-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-fri-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-fri-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-fri-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-fri-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-fri-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sat-alt-start-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            end_time = moment($("#course-sat-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sat-alt-end-time").timepicker("setTime", start_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
        $("#course-sat-alt-end-time").timepicker().on("changeTime.timepicker", function (event) {
            start_time = moment($("#course-sat-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT);
            end_time = moment(event.time.value, helium.HE_TIME_STRING_CLIENT);
            if (start_time.isAfter(end_time)) {
                $("#course-sat-alt-start-time").timepicker("setTime", end_time.format(helium.HE_TIME_STRING_CLIENT));
            }
        });
    };

    /**
     * Save changes to the course.
     */
    this.save_course = function () {
        helium.ajax_error_occurred = false;

        var course_title = $("#course-title").val(), course_start_date = $("#course-start-date").val(), course_end_date = $("#course-end-date").val(), start_date, end_date, data, different_times, sun_start_time, sun_end_time, sun_alt_start_time, sun_alt_end_time;

        self.clear_course_errors();

        // Validate
        if (/\S/.test(course_title) && course_start_date !== "" && course_end_date !== "") {
            $("#loading-course-modal").spin(helium.SMALL_LOADING_OPTS);

            start_date = moment(course_start_date).format(helium.HE_DATE_STRING_SERVER);
            end_date = moment(course_end_date).format(helium.HE_DATE_STRING_SERVER);
            if ($("#course-group").val() === "") {
                data = {
                    "title": "Unnamed Group",
                    "start_date": start_date,
                    "end_date": end_date,
                    "shown_on_calendar": true,
                    "average_grade": -1
                };

                self.ajax_calls.push(helium.planner_api.add_course_group(function (data) {
                    self.add_course_group_to_page(data);

                    $("#course-group").val(data.id);
                }, data));
            }

            // If a course group was created, wait for that call to complete before proceeding
            $.when.apply(this, self.ajax_calls).done(function () {
                if (!helium.ajax_error_occurred) {
                    var categories_data = [], id;
                    different_times = $("#course-schedule-has-different-times").is(":checked");
                    sun_start_time = moment($("#course-sun-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER);
                    sun_end_time = moment($("#course-sun-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER);
                    sun_alt_start_time = moment($("#course-sun-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER);
                    sun_alt_end_time = moment($("#course-sun-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER);

                    // Build a JSONifyable list of category elements
                    $("[id^='category-'][id$='-modified']").each(function () {
                        helium.planner_api.edit_category(function () {
                            },
                            self.course_group_id, self.edit_id, $(this).attr("id").split("category-")[1].split("-modified")[0],
                            {
                                "title": $($(this).children()[0]).text(),
                                "weight": $($(this).children()[1]).text() != "N/A" ? $($(this).children()[1]).text().slice(0, -1) : 0
                            });
                    });

                    $("[id^='category-'][id$='-unsaved']").each(function () {
                        categories_data.push({
                            "title": $($(this).children()[0]).text(),
                            "weight": $($(this).children()[1]).text() != "N/A" ? $($(this).children()[1]).text().slice(0, -1) : 0
                        });
                    });

                    data = {
                        "title": course_title,
                        "start_date": start_date,
                        "end_date": end_date,
                        "room": $("#course-room").val(),
                        "credits": $("#course-credits").val(),
                        "days_of_week": ($("#course-schedule-sun").hasClass("active") ? "1" : "0") + ($("#course-schedule-mon").hasClass("active") ? "1" : "0") + ($("#course-schedule-tue").hasClass("active") ? "1" : "0") + ($("#course-schedule-wed").hasClass("active") ? "1" : "0") + ($("#course-schedule-thu").hasClass("active") ? "1" : "0") + ($("#course-schedule-fri").hasClass("active") ? "1" : "0") + ($("#course-schedule-sat").hasClass("active") ? "1" : "0"),
                        "sun_start_time": sun_start_time,
                        "sun_end_time": sun_end_time,
                        "mon_start_time": different_times ? moment($("#course-mon-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "mon_end_time": different_times ? moment($("#course-mon-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "tue_start_time": different_times ? moment($("#course-tue-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "tue_end_time": different_times ? moment($("#course-tue-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "wed_start_time": different_times ? moment($("#course-wed-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "wed_end_time": different_times ? moment($("#course-wed-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "thu_start_time": different_times ? moment($("#course-thu-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "thu_end_time": different_times ? moment($("#course-thu-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "fri_start_time": different_times ? moment($("#course-fri-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "fri_end_time": different_times ? moment($("#course-fri-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "sat_start_time": different_times ? moment($("#course-sat-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_start_time,
                        "sat_end_time": different_times ? moment($("#course-sat-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_end_time,
                        "days_of_week_alt": ($("#course-schedule-sun-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-mon-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-tue-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-wed-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-thu-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-fri-alt").hasClass("active") ? "1" : "0") + ($("#course-schedule-sat-alt").hasClass("active") ? "1" : "0"),
                        "sun_start_time_alt": sun_alt_start_time,
                        "sun_end_time_alt": sun_alt_end_time,
                        "mon_start_time_alt": different_times ? moment($("#course-mon-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "mon_end_time_alt": different_times ? moment($("#course-mon-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "tue_start_time_alt": different_times ? moment($("#course-tue-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "tue_end_time_alt": different_times ? moment($("#course-tue-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "wed_start_time_alt": different_times ? moment($("#course-wed-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "wed_end_time_alt": different_times ? moment($("#course-wed-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "thu_start_time_alt": different_times ? moment($("#course-thu-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "thu_end_time_alt": different_times ? moment($("#course-thu-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "fri_start_time_alt": different_times ? moment($("#course-fri-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "fri_end_time_alt": different_times ? moment($("#course-fri-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "sat_start_time_alt": different_times ? moment($("#course-sat-alt-start-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_start_time,
                        "sat_end_time_alt": different_times ? moment($("#course-sat-alt-end-time").val(), helium.HE_TIME_STRING_CLIENT).format(helium.HE_TIME_STRING_SERVER) : sun_alt_end_time,
                        "color": $("#id_course_color").val(),
                        "website": $("#course-website").val(),
                        "is_online": $("#course-online").is(":checked"),
                        "teacher_name": $("#course-teacher-name").val(),
                        "teacher_email": $("#course-teacher-email").val(),
                        "course_group": $("#course-group").val()
                    };
                    if (self.edit) {
                        helium.planner_api.edit_course(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-course-modal").spin(false);

                                $("#course-error").html(data[0].err_msg);
                                $("#course-error").parent().show("fast");
                            } else {
                                $.each(categories_data, function (i, category_data) {
                                    helium.classes.ajax_calls.push(helium.planner_api.add_category(function () {
                                        if (helium.data_has_err_msg(data)) {
                                            helium.ajax_error_occurred = true;
                                            $("#loading-courses").spin(false);

                                            $("#course-error").html(data[0].err_msg);
                                            $("#course-error").parent().show("fast");

                                            return false;
                                        }
                                    }, self.course_group_id, self.edit_id, category_data));
                                });

                                if (!helium.ajax_error_occurred) {
                                    $.each(helium.classes.categories_to_delete, function (i, category_id) {
                                        helium.classes.ajax_calls.push(helium.planner_api.delete_category(function () {
                                            if (helium.data_has_err_msg(data)) {
                                                helium.ajax_error_occurred = true;
                                                $("#loading-courses").spin(false);

                                                $("#course-error").html(data[0].err_msg);
                                                $("#course-error").parent().show("fast");

                                                return false;
                                            }
                                        }, self.course_group_id, self.edit_id, category_id));
                                    });
                                }

                                if (!helium.ajax_error_occurred) {
                                    $.each(helium.classes.attachments_to_delete, function (i, attachment_id) {
                                        helium.classes.ajax_calls.push(helium.planner_api.delete_attachment(function () {
                                            if (helium.data_has_err_msg(data)) {
                                                helium.ajax_error_occurred = true;
                                                $("#loading-courses").spin(false);

                                                $("#course-error").html(data[0].err_msg);
                                                $("#course-error").parent().show("fast");

                                                return false;
                                            }
                                        }, attachment_id));
                                    });
                                }

                                $.when.apply(this, helium.classes.ajax_calls).done(function () {
                                    if (!helium.ajax_error_occurred) {
                                        helium.classes.categories_to_delete = [];
                                        helium.classes.attachments_to_delete = [];

                                        var row_div = $("#course-" + data.id);
                                        self.course_group_table[data.course_group.toString()].cell(row_div, 0).data("<span class=\"label label-sm\" style=\"background-color: " + data.color + " !important\">" + (data.website !== "" ? "<a target=\"_blank\" href=\"" + data.website + "\" class=\"course-title-with-link\">" + data.title + " <i class=\"icon-external-link bigger-110\"></i></a>" : data.title) + "</span>");
                                        self.course_group_table[data.course_group.toString()].cell(row_div, 1).data(moment(data.start_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT) + " to " + moment(data.end_date, helium.HE_DATE_STRING_SERVER).format(helium.HE_DATE_STRING_CLIENT));
                                        self.course_group_table[data.course_group.toString()].cell(row_div, 2).data(data.room);
                                        self.course_group_table[data.course_group.toString()].cell(row_div, 3).data(data.teacher_email !== "" ? ("<a target=\"_blank\" href=\"mailto:" + data.teacher_email + "\" class=\"teacher-email-with-link\">" + data.teacher_name + "</a>") : data.teacher_name);
                                        self.course_group_table[data.course_group.toString()].cell(row_div, 4).data(self.get_schedule(data));
                                        self.course_group_table[data.course_group.toString()].draw();
                                        // Bind clickable attributes to their respective handlers
                                        row_div.find(".course-title-with-link").on("click", function (e) {
                                            e.stopImmediatePropagation();
                                        });
                                        row_div.on("click", function () {
                                            self.edit_course_btn($(this).find("#edit-course-" + data.id), true);
                                        });
                                        row_div.find("#edit-course-" + data.id).on("click", function () {
                                            self.edit_course_btn($(this), true);
                                        });
                                        row_div.find("#delete-course-" + data.id).on("click", function (e) {
                                            e.stopPropagation();
                                            self.delete_course_btn($(this));
                                        });

                                        if (self.dropzone !== null && self.dropzone.getQueuedFiles().length > 0) {
                                            self.dropzone.processQueue();
                                        } else {
                                            $("#loading-course-modal").spin(false);
                                            $("#course-modal").modal("hide");
                                        }
                                    }
                                });
                            }
                        }, data["course_group"], self.edit_id, data);
                    } else {
                        data.current_grade = -1;

                        helium.planner_api.add_course(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-course-modal").spin(false);

                                $("#course-error").html(data[0].err_msg);
                                $("#course-error").parent().show("fast");
                            } else {
                                $.each(categories_data, function (i, category_data) {
                                    helium.classes.ajax_calls.push(helium.planner_api.add_category(function () {
                                        if (helium.data_has_err_msg(data)) {
                                            helium.ajax_error_occurred = true;
                                            $("#loading-courses").spin(false);

                                            $("#course-error").html(data[0].err_msg);
                                            $("#course-error").parent().show("fast");

                                            return false;
                                        }
                                    }, data.course_group, data.id, category_data));
                                });

                                if (!helium.ajax_error_occurred) {
                                    $.each(helium.classes.categories_to_delete, function (i, category_id) {
                                        helium.classes.ajax_calls.push(helium.planner_api.delete_category(function () {
                                            if (helium.data_has_err_msg(data)) {
                                                helium.ajax_error_occurred = true;
                                                $("#loading-courses").spin(false);

                                                $("#course-error").html(data[0].err_msg);
                                                $("#course-error").parent().show("fast");

                                                return false;
                                            }
                                        }, data.course_group, data.id, category_id));
                                    });
                                }

                                if (!helium.ajax_error_occurred) {
                                    $.each(helium.classes.attachments_to_delete, function (i, attachment_id) {
                                        helium.classes.ajax_calls.push(helium.planner_api.delete_attachment(function () {
                                            if (helium.data_has_err_msg(data)) {
                                                helium.ajax_error_occurred = true;
                                                $("#loading-courses").spin(false);

                                                $("#course-error").html(data[0].err_msg);
                                                $("#course-error").parent().show("fast");

                                                return false;
                                            }
                                        }, attachment_id));
                                    });
                                }

                                $.when.apply(this, helium.classes.ajax_calls).done(function () {
                                    if (!helium.ajax_error_occurred) {
                                        helium.classes.categories_to_delete = [];
                                        helium.classes.attachments_to_delete = [];

                                        self.add_course_to_groups(data, self.course_group_table[data.course_group.toString()]);
                                        self.course_group_table[data.course_group.toString()].draw();

                                        if (self.dropzone !== null && self.dropzone.getQueuedFiles().length > 0) {
                                            self.edit = true;
                                            self.edit_id = data.id;
                                            self.dropzone.processQueue();
                                        } else {
                                            $("#loading-course-modal").spin(false);
                                            $("#course-modal").modal("hide");
                                        }
                                    }
                                });
                            }
                        }, data["course_group"], data);
                    }
                }
            });
        } else {
            // Validation failed, so don't save and prompt the user for action
            $("#course-error").html("You must specify values for fields highlighted in red.");
            $("#course-error").parent().show("fast");

            if (!/\S/.test(course_title)) {
                $("#course-title").parent().parent().addClass("has-error");
            }
            if (course_start_date === "") {
                $("#course-start-date").parent().parent().addClass("has-error");
            }
            if (course_end_date === "") {
                $("#course-end-date").parent().parent().addClass("has-error");
            }

            $("a[href='#course-panel-tab-1']").tab("show");
        }
    };

    /**
     * Refresh the list of course groups.
     */
    this.refresh_course_groups = function () {
        var id, title;
        self.course_groups = {};
        $("table[id^='course-group-table-']").each(function () {
            id = $(this).attr("id").split("course-group-table-")[1];
            title = $("#course-group-title-" + id).html();
            self.course_groups[id] = {
                id: id,
                title: title,
                start_date: $("#course-group-" + id + "-start-date").html().trim(),
                end_date: $("#course-group-" + id + "-end-date").html().split("to ")[1].trim()
            };
        });
    };
}

// Initialize HeliumClasses and give a reference to the Helium object
helium.classes = new HeliumClasses();

/*******************************************
 * jQuery initialization
 ******************************************/

$(document).ready(function () {
    "use strict";

    $("#loading-courses").spin(helium.SMALL_LOADING_OPTS);
    $("#loading-course-group-modal").spin(false);
    $("#loading-course-modal").spin(false);

    /*******************************************
     * Initialize component libraries
     ******************************************/
    bootbox.setDefaults({
        locale: 'en'
    });

    helium.classes.initialize_datetime();

    $(".spinner").spinner({
        min: 0.0,
        step: 0.25,
        page: 4,
        numberFormat: "n",
        create: function () {
            $(this).next().addClass("btn btn-success").html('<i class="icon-plus"></i>').next().addClass("btn btn-danger").html('<i class="icon-minus"></i>');
            // Correct CSS for touch displays
            if (ace.click_event === "tap") {
                $(this).closest(".ui-spinner").addClass("ui-spinner-touch");
            }
        }
    });
    $("#id_course_color").simplecolorpicker({picker: true, theme: "glyphicons"});

    /*******************************************
     * Other page initialization
     ******************************************/
    helium.planner_api.get_course_groups(function (data) {
        $.each(data, function (i, course_group_data) {
            helium.classes.add_course_group_to_page(course_group_data);
        });
    }, false);

    helium.classes.refresh_course_groups();

    $("table[id^='course-group-table-']").each(function () {
        var id = $(this).attr("id").split("course-group-table-")[1].split("_")[0], table_div = $(this), i = 0;

        if (!helium.ajax_error_occurred) {
            helium.classes.ajax_calls.push(helium.planner_api.get_courses_by_course_group_id(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-courses").spin(false);

                    bootbox.alert(data[0].err_msg);
                } else {
                    for (i = 0; i < data.length; i += 1) {
                        helium.classes.add_course_to_groups(data[i], helium.classes.course_group_table[id]);
                    }
                    helium.classes.course_group_table[id].draw();

                    $("#course-group-table-" + id + "_filter label input").attr("placeholder", "Search ...").wrap("<span class=\"input-icon hidden-xs\" id=\"search-bar\">").parent().append("<i class=\"icon-search nav-search-icon\"></i>");
                    $($("#course-group-table-" + id + "_filter label").contents()[0]).remove();
                }
            }, id));
        }
    });

    $.when.apply(this, helium.classes.ajax_calls).done(function () {
        if (!helium.ajax_error_occurred) {
            /*******************************************
             * Check cookies for triggers passed in
             ******************************************/
            if ($.cookie("edit_categories")) {
                var course_id = $.cookie("course_id");

                helium.classes.edit_course_btn($("#edit-course-" + course_id), false);
                $("a[href='#course-panel-tab-3']").tab("show");

                $.removeCookie("course_id", {path: "/"});
                $.removeCookie("edit_categories", {path: "/"});
            }

            if ($("#course-group-tabs a").length === 1) {
                $("#no-classes-tab").addClass("active");
            }

            $("#loading-courses").spin(false);
        }
    });

    Dropzone.autoDiscover = false;
    try {
        $(".dropzone").dropzone({
            maxFilesize: 10,
            addRemoveLinks: true,
            autoProcessQueue: false,
            uploadMultiple: true,
            parallelUploads: 10,
            dictDefaultMessage: "<span class=\"bigger-150 bolder\"><i class=\"icon-caret-right red\"></i> Drop file</span> to upload <span class=\"smaller-80 grey\">(or click)</span> <br /> <i class=\"upload-icon icon-cloud-upload blue icon-3x\"></i>",
            dictResponseError: "Error while uploading file!",
            previewTemplate: "<div class=\"dz-preview dz-file-preview\">\n  <div class=\"dz-details\">\n    <div class=\"dz-filename\"><span data-dz-name></span></div>\n    <div class=\"dz-size\" data-dz-size></div>\n    <img data-dz-thumbnail />\n  </div>\n  <div class=\"progress progress-small progress-striped active\"><div class=\"progress-bar progress-bar-success\" data-dz-uploadprogress></div></div>\n  <div class=\"dz-success-mark\"><span></span></div>\n  <div class=\"dz-error-mark\"><span></span></div>\n  <div class=\"dz-error-message\"><span data-dz-errormessage></span></div>\n</div>",
            init: function () {
                helium.classes.dropzone = this;
                var CSRF_TOKEN = $.cookie("csrftoken");

                this.on("sendingmultiple", function (na, xhr, form_data) {
                    xhr.setRequestHeader("X-CSRFToken", CSRF_TOKEN);
                    form_data.append("course", helium.classes.edit_id);
                });
                this.on("successmultiple", function (files) {
                    $("#loading-course-modal").spin(false);
                    $("#course-modal").modal("hide");
                });
                this.on("errormultiple", function () {
                    $("#loading-course-modal").spin(false);

                    $("#course-error").html("The class is saved, but an error occurred while uploading attachments. If the error persists, <a href=\"/support\">contact support</a>.");
                    $("#course-error").parent().show("fast");

                    $("a[href='#course-panel-tab-4']").tab("show");

                    helium.classes.dropzone.removeAllFiles();
                });
            }
        });
    } catch (e) {
        helium.classes.dropzone = null;
        bootbox.alert("Attachments are not supported in older browsers.");
    }
});

$("#course-modal, #course-group-modal").scroll(function () {
    "use strict";

    $('.date-picker').datepicker('place');
});