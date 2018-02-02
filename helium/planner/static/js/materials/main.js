/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript functionality for persistence and the HeliumMaterials object on the /planner/materials page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.1
 */

/**
 * Create the HeliumMaterials persistence object.
 *
 * @constructor construct the HeliumMaterials persistence object
 */
function HeliumMaterials() {
    "use strict";

    helium.MATERIAL_STATUS_CHOICES = [
        "Owned",
        "Rented",
        "Ordered",
        "Shipped",
        "Need",
        "Received",
        "To Sell"
    ];

    this.ajax_calls = [];
    this.material_group_table = {};
    this.edit = false;
    this.edit_id = -1;
    this.courses = {};

    var self = this;

    /*******************************************
     * Functions
     ******************************************/

    /**
     * Revert persistence for adding/editing a MaterialGroup.
     */
    this.nullify_material_group_persistence = function () {
        self.edit = false;
        self.edit_id = -1;
        helium.ajax_error_occurred = false;
    };

    /**
     * Revert persistence for adding/editing a Material.
     */
    this.nullify_material_persistence = function () {
        self.edit = false;
        self.edit_id = -1;
        helium.ajax_error_occurred = false;
    };

    /**
     * Clear Material marked in the Material modal.
     */
    this.clear_material_errors = function () {
        helium.ajax_error_occurred = false;
        $("#material-title").parent().parent().removeClass("has-error");
    };

    /**
     * Clear MaterialGroup marked in the MaterialGroup modal.
     */
    this.clear_material_group_errors = function () {
        helium.ajax_error_occurred = false;
        $("#material-group-title").parent().parent().removeClass("has-error");
    };

    /**
     * Create a new material in the currently open material group.
     */
    this.create_material_for_group_btn = function () {
        self.edit = false;

        // First, ensure we have a material group to add the new material to
        $("#material-modal-label").html("Add Material");
        $("#material-title").val("");
        $("#material-courses").val("");
        $("#material-courses").trigger("change");
        $("#material-courses").trigger("chosen:updated");

        $("#material-group").val($("#material-group-tabs li.active a").attr("href") ? $("#material-group-tabs li.active a").attr("href").split("material-group-")[1] : "");

        $("#material-status").val("0");
        $("#material-condition").val("0");
        $("#material-website").val("");
        $("#material-price").val("");
        $("#material-details").html("");

        $("#loading-material-modal").spin(false);
        $("#material-modal").modal("show");
    };

    /**
     * Add the given material group's data to the page.
     *
     * @param data the data for the material group to be added
     */
    this.add_material_group_to_page = function (data) {
        helium.ajax_error_occurred = false;

        if (helium.data_has_err_msg(data)) {
            helium.ajax_error_occurred = true;
            $("#loading-material-group-modal").spin(false);

            $("#material-error").html(helium.get_error_msg(data));
            $("#material-error").parent().show("fast");
        } else {
            var input_tab, material_group_div, div, table_div;
            $.each($('a[href^="#material-group-"]'), function (index, tab) {
                if (!input_tab && data.title < $.trim($(tab).text())) {
                    input_tab = tab;
                }
            });
            if (input_tab) {
                input_tab = $(input_tab).parent();
            } else {
                input_tab = $("#create-material-group-li");
            }
            input_tab.before("<li><a data-toggle=\"tab\" href=\"#material-group-" + data.id + "\"><i class=\"icon-briefcase r-110\"></i> " + data.title + (!data.shown_on_calendar ? " (H)" : "") + "</a></li>");
            material_group_div = "<div id=\"material-group-" + data.id + "\" class=\"tab-pane\"><div class=\"col-sm-12\"><div class=\"table-header\"><span id=\"material-group-title-" + data.id + "\">" + data.title + (!data.shown_on_calendar ? " (Hidden)" : "") + "</span></span><label class=\"pull-right inline action-buttons\" style=\"padding-right: 10px\"><a class=\"cursor-hover\" id=\"create-material-for-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-plus-sign-alt bigger-120 hidden-print\"></i></span></a>&nbsp;<a class=\"cursor-hover\" id=\"edit-material-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-edit bigger-120 hidden-print\"></i></span>&nbsp;</a><a class=\"cursor-hover\" id=\"delete-material-group-" + data.id + "\"><span class=\"white\"><i class=\"icon-trash bigger-120 hidden-print\"></i></span></a></label></div><div class=\"table-responsive\"><table id=\"material-group-table-" + data.id + "\" class=\"table table-striped table-bordered table-hover\"><thead><tr><th>Title</th><th class=\"hidden-xs\">Price</th><th class=\"hidden-xs\">Status</th><th class=\"hidden-xs\">Classes</th><th>Details</th><th class=\"hidden-xs\"></th></tr></thead><tbody id=\"material-group-table-body-" + data.id + "\"></tbody></table></div></div></div>";
            // Determine the placement for this tab
            div = $("#material-group-tab-content").append(material_group_div);
            // Bind clickable attributes to their respective handlers
            div.find("#create-material-for-group-" + data.id).on("click", function () {
                self.create_material_for_group_btn();
            });
            div.find("#edit-material-group-" + data.id).on("click", function () {
                self.edit_material_group_btn($(this));
            });
            div.find("#delete-material-group-" + data.id).on("click", function () {
                self.delete_material_group_btn($(this));
            });

            table_div = div.find("#material-group-table-" + data.id).dataTable({
                aoColumns: [
                    null, {sClass: "hidden-xs"}, {sClass: "hidden-xs"}, {sClass: "hidden-xs"}, null, {
                        bSortable: false,
                        bSearchable: false,
                        sClass: "hidden-xs",
                        sWidth: "90px"
                    }
                ],
                stateSave: true
            });
            self.material_group_table[data.id] = table_div.DataTable();
            table_div.parent().find("#material-group-table-" + data.id + "_length").addClass("hidden-print");
            table_div.parent().find("#material-group-table-" + data.id + "_filter").addClass("hidden-print");
            table_div.parent().find("#material-group-table-" + data.id + "_info").parent().parent().addClass("hidden-print");

            self.nullify_material_group_persistence();

            $("#material-group-table-" + data.id + "_filter label input").attr("placeholder", "Search ...").wrap("<span class=\"input-icon\" id=\"search-bar\">").parent().append("<i class=\"icon-search nav-search-icon\"></i>");
            $($("#material-group-table-" + data.id + "_filter label").contents()[0]).remove();

            $("#loading-material-group-modal").spin(false);
            $("#material-group-modal").modal("hide");

            $("#material-group-tabs li a[href='#material-group-" + data.id + "']").tab("show");
        }
    };

    /**
     * Show the Material Group modal to edit a material group.
     *
     * @param selector the selector for the edit button of a material group
     */
    this.edit_material_group_btn = function (selector) {
        helium.ajax_error_occurred = false;

        if (!self.edit) {
            $("#loading-materials").spin(helium.SMALL_LOADING_OPTS);
            self.edit = true;
            $("#material-group-modal-label").html("Edit Group");
            // Initialize dialog attributes for editing
            self.edit_id = selector.attr("id").split("edit-material-group-")[1];
            helium.planner_api.get_material_group(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-materials").spin(false);
                    self.edit = false;
                    self.edit_id = -1;

                    bootbox.alert(helium.get_error_msg(data));
                } else {
                    var material_group = data;
                    $("#material-group-title").val(material_group.title);
                    $("#material-group-shown-on-calendar").prop("checked", !material_group.shown_on_calendar);

                    $("#loading-material-group-modal").spin(false);
                    $("#loading-materials").spin(false);
                    $("#material-group-modal").modal("show");
                }
            }, self.edit_id);
        }
    };

    /**
     * Delete the given material group.
     *
     * @param selector the selector for the edit button of a material group
     */
    this.delete_material_group_btn = function (selector) {
        helium.ajax_error_occurred = false;

        var id = selector.attr("id").split("delete-material-group-")[1];
        bootbox.dialog({
            message: "Deleting this group will permanently delete all materials associated with it.",
            buttons: {
                "delete": {
                    "label": '<i class="icon-trash"></i> Delete',
                    "className": "btn-sm btn-danger",
                    "callback": function () {
                        $("#loading-materials").spin(helium.SMALL_LOADING_OPTS);
                        helium.planner_api.delete_material_group(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-materials").spin(false);

                                bootbox.alert(helium.get_error_msg(data));
                            } else {
                                $("#material-group-" + id).slideUp("fast", function () {
                                    var parent = $('a[href="#material-group-' + id + '"]').parent();
                                    if (parent.prev().length > 0) {
                                        parent.prev().find("a").tab("show");
                                    } else if (parent.next().length > 0 && !parent.next().is($("#create-material-group-li"))) {
                                        parent.next().find("a").tab("show");
                                    } else {
                                        $("#no-materials-tab").addClass("active");
                                    }

                                    $(this).remove();
                                    $('a[href="#material-group-' + id + '"]').parent().remove();
                                    $("#loading-materials").spin(false);
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
     * Show the Material modal to edit a material.
     *
     * @param selector the selector for the edit button of a material
     */
    this.edit_material_btn = function (selector) {
        helium.ajax_error_occurred = false;

        if (!self.edit) {
            $("#loading-materials").spin(helium.SMALL_LOADING_OPTS);
            self.edit = true;
            $("#material-modal-label").html("Edit Material");

            // Initialize dialog attributes for editing
            self.edit_id = selector.attr("id").split("edit-material-")[1];
            self.material_group_id = parseInt(selector.closest("[id^='material-group-table-']").attr('id').split('material-group-table-body-')[1]);
            helium.planner_api.get_material(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;
                    $("#loading-materials").spin(false);
                    self.edit = false;
                    self.edit_id = -1;

                    bootbox.alert(helium.get_error_msg(data));
                } else {
                    var material = data;

                    // Change display to the correct material group tab
                    $('a[href="#material-group-' + material.material_group + '"]').tab("show");

                    $("#material-title").val(material.title);

                    $("#material-group").val(material.material_group);
                    $("#material-courses").val(material.courses);
                    $("#material-courses").trigger("change");
                    $("#material-courses").trigger("chosen:updated");
                    $("#material-status").val(material.status);
                    $("#material-status").trigger("change");
                    $("#material-status").trigger("chosen:updated");
                    $("#material-condition").val(material.condition);
                    $("#material-condition").trigger("change");
                    $("#material-condition").trigger("chosen:updated");
                    $("#material-website").val(material.website);
                    $("#material-price").val(material.price);
                    $("#material-details").html(material.details);

                    $("#loading-material-modal").spin(false);
                    $("#loading-materials").spin(false);
                    $("#material-modal").modal("show");
                }
            }, self.material_group_id, self.edit_id);
        }
    };

    /**
     * Delete the given material.
     *
     * @param selector the selector for the edit button of a material
     */
    this.delete_material_btn = function (selector) {
        helium.ajax_error_occurred = false;

        var id = selector.attr("id").split("delete-material-")[1];
        var material_group_id = parseInt(selector.closest("[id^='material-group-table-']").attr('id').split('material-group-table-body-')[1]);
        bootbox.dialog({
            message: "Are you sure you want to delete this material?",
            buttons: {
                "delete": {
                    "label": '<i class="icon-trash"></i> Delete',
                    "className": "btn-sm btn-danger",
                    "callback": function () {
                        $("#loading-materials").spin(helium.SMALL_LOADING_OPTS);
                        self.ajax_calls.push(helium.planner_api.delete_material(function (data) {
                            if (helium.data_has_err_msg(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-materials").spin(false);

                                bootbox.alert(helium.get_error_msg(data));
                            } else {
                                $("#material-" + id).slideUp("fast", function () {
                                    self.material_group_table[$("#material-group-tabs li.active a").attr("href").split("#material-group-")[1]].row($(this)).remove().draw();

                                    $("#loading-materials").spin(false);
                                });
                            }
                        }, material_group_id, id));
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
     * Add a material to the given material group.
     *
     * @param material_data the material data with which to build the material
     * @param table the material group table in which to add the material
     */
    this.add_material_to_group = function (material_data, table) {
        var row = table.row.add([material_data.website !== "" ? "<a target=\"_blank\" class=\"material-with-link\" href=\"" + material_data.website + "\">" + material_data.title + "</a>" : material_data.title, material_data.price, helium.MATERIAL_STATUS_CHOICES[material_data.status], self.get_course_names(material_data.courses), helium.get_comments_with_link(material_data.details), "<div class=\"hidden-xs action-buttons\"><a class=\"green cursor-hover\" id=\"edit-material-" + material_data.id + "\"><i class=\"icon-edit bigger-130\"></i></a><a class=\"red cursor-hover\" id=\"delete-material-" + material_data.id + "\"><i class=\"icon-trash bigger-130\"></i></a></div>"]).node(), row_div = $(row).attr("id", "material-" + material_data.id);
        row_div.find(".material-with-link").on("click", function (e) {
            e.stopImmediatePropagation();
        });
        // Bind clickable attributes to their respective handlers
        row_div.on("click", function () {
            self.edit_material_btn($(this).find("#edit-material-" + material_data.id));
        });
        row_div.find("#edit-material-" + material_data.id).on("click", function () {
            self.edit_material_btn($(this));
        });
        row_div.find("#delete-material-" + material_data.id).on("click", function (e) {
            e.stopPropagation();
            self.delete_material_btn($(this));
        });
    };

    /**
     * Retrieve the string list of course names for the list of IDs.
     *
     * @param ids of courses
     */
    this.get_course_names = function (ids) {
        var course_names = "", i = 0;

        for (i = 0; i < ids.length; i += 1) {
            course_names += ("<span class=\"label label-sm\" style=\"background-color: " + self.courses[ids[i]].color + " !important\">" + self.courses[ids[i]].title + "</span> ");
        }

        return course_names;
    };

    /**
     * Resort material groups alphabetically.
     */
    this.resort_material_groups = function () {
        var group_tabs = $('a[href^="#material-group-"]'), swapped = true, i = 1, tab = null, prev_tab = null, prev = null;

        // Good 'ol bubble sort the entries
        while (swapped) {
            swapped = false;
            for (i = 1; i < group_tabs.length; i += 1) {
                tab = group_tabs[i];
                prev_tab = group_tabs[i - 1];
                if ($.trim($(tab).text()) < $.trim($(prev_tab).text())) {
                    $(prev_tab).parent().before($(tab).parent());

                    prev = group_tabs[i];
                    group_tabs[i] = group_tabs[i - 1];
                    group_tabs[i - 1] = prev;

                    swapped = true;
                }
            }
        }
    };
}

// Initialize HeliumMaterials and give a reference to the Helium object
helium.materials = new HeliumMaterials();

/*******************************************
 * jQuery initialization
 ******************************************/

$(document).ready(function () {
    "use strict";

    $("#loading-materials").spin(helium.SMALL_LOADING_OPTS);
    $("#loading-material-group-modal").spin(false);
    $("#loading-material-modal").spin(false);

    /*******************************************
     * Initialize component libraries
     ******************************************/
    $("#material-courses").chosen({width: "100%", search_contains: true, no_results_text: "No classes match"});

    bootbox.setDefaults({
        locale: 'en'
    });

    /*******************************************
     * Other page initialization
     ******************************************/
    $(".wysiwyg-editor").ace_wysiwyg({
        toolbar: [
            "bold", "italic", "underline", null, "insertunorderedlist", "insertorderedlist", null, "undo", "redo"
        ]
    }).prev().addClass("wysiwyg-style2");

    helium.materials.ajax_calls.push(helium.planner_api.get_all_courses_by_user_id(function (data) {
        if (helium.data_has_err_msg(data)) {
            helium.ajax_error_occurred = true;
            $("#loading-materials").spin(false);

            bootbox.alert(helium.get_error_msg(data));
        } else {
            $.each(data, function (index, course) {
                helium.materials.courses[course.id] = course;
                $("#material-courses").append("<option value=\"" + course.id + "\">" + course.title + "</option>");
            });

            if (data.length <= 0) {
                $("#material-courses-form-group").hide("fast");
            } else {
                $("#material-courses-form-group").show("fast");
            }

            $("#material-courses").prop("disabled", data.length === 0).trigger("chosen:updated");
        }
    }, helium.USER_PREFS.id));

    helium.planner_api.get_material_groups(function (data) {
        $.each(data, function (i, material_group_data) {
            helium.materials.add_material_group_to_page(material_group_data);
        });
    }, false);

    $("#material-group-tabs li a[href^='#material-group-']").first().tab("show");

    $.when.apply(this, helium.materials.ajax_calls).done(function () {
        if (!helium.ajax_error_occurred) {
            $("table[id^='material-group-table-']").each(function () {
                var i = 0, id = $(this).attr("id").split("material-group-table-")[1], table_div = $(this);

                if (!helium.ajax_error_occurred) {
                    helium.materials.ajax_calls.push(helium.planner_api.get_materials_by_material_group_id(function (data) {
                        if (helium.data_has_err_msg(data)) {
                            helium.ajax_error_occurred = true;
                            $("#loading-materials").spin(false);

                            bootbox.alert(helium.get_error_msg(data));
                        } else {
                            for (i = 0; i < data.length; i += 1) {
                                helium.materials.add_material_to_group(data[i], helium.materials.material_group_table[id]);
                            }
                            helium.materials.material_group_table[id].draw();

                            $("#material-group-table-" + id + "_filter label input").attr("placeholder", "Search ...").wrap("<span class=\"input-icon hidden-xs\" id=\"search-bar\">").parent().append("<i class=\"icon-search nav-search-icon\"></i>");
                            $($("#material-group-table-" + id + "_filter label").contents()[0]).remove();
                        }
                    }, id));
                }
            });
        }
    });

    $.when.apply(this, helium.materials.ajax_calls).done(function () {
        if ($("#material-group-tabs a").length === 1) {
            $("#no-materials-tab").addClass("active");
        }

        $("#loading-materials").spin(false);
    });

    $("#material-group-title").on('keydown', function (event) {
        var x = event.which;
        if (x === 13) {
            event.preventDefault();
        }
    });
});