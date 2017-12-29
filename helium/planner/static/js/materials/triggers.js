/**
 * Copyright (c) 2017 Helium Edu.
 *
 * JavaScript functionality for triggers on the the /planner/materials page.
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

    $("#material-group-modal").on("shown.bs.modal", function () {
        $("#material-group-title").focus();
    });

    $("#material-modal, #material-group-modal").on("hidden.bs.modal", function () {
        helium.materials.nullify_material_persistence();
        helium.materials.nullify_material_group_persistence();
        $("#material-error, #material-group-error").parent().hide("fast");

        helium.materials.clear_material_errors();
        helium.materials.clear_material_group_errors();
    });

    // MaterialGroup components
    $("#save-material-group").on("click", function () {
        helium.ajax_error_occurred = false;

        var material_group_title = $("#material-group-title").val(), data;

        helium.materials.clear_material_group_errors();

        // Validate
        if (/\S/.test(material_group_title)) {
            $("#loading-material-group-modal").spin(helium.SMALL_LOADING_OPTS);

            data = {
                "title": material_group_title,
                "shown_on_calendar": !$("#material-group-shown-on-calendar").prop("checked")
            };
            if (helium.materials.edit) {
                helium.planner_api.edit_material_group(function (data) {
                    if (helium.is_data_invalid(data)) {
                        helium.ajax_error_occurred = true;
                        $("#loading-material-group-modal").spin(false);

                        if (helium.data_has_err_msg(data)) {
                            $("#material-group-error").html(data[0].err_msg);
                        } else {
                            $("#material-group-error").html("Oops, an unknown error has occurred. If the error persists, <a href=\"/support\">contact support</a>.");
                        }
                        $("#material-group-error").parent().show("fast");
                    } else {
                        var material_group = data;
                        $('a[href="#material-group-' + data.id + '"]').html("<i class=\"icon-briefcase r-110\"></i> <span class=\"hidden-xs\">" + material_group.title + (!material_group.shown_on_calendar ? " (H)" : "") + "</span>");
                        $("#material-group-title-" + data.id).html(material_group.title + (!material_group.shown_on_calendar ? " (Hidden)" : ""));

                        helium.materials.resort_material_groups();

                        $("#loading-material-group-modal").spin(false);
                        $("#material-group-modal").modal("hide");
                    }
                }, helium.materials.edit_id, data);
            } else {
                helium.planner_api.add_material_group(helium.materials.add_material_group_to_page, data);
            }
        } else {
            // Validation failed, so don't save and prompt the user for action
            $("#material-group-error").html("You must specify values for fields highlighted in red.");
            $("#material-group-error").parent().show("fast");

            if (!/\S/.test(material_group_title)) {
                $("#material-group-title").parent().parent().addClass("has-error");
            }
        }
    });

    $("#create-material-group").on("click", function () {
        helium.materials.edit = false;
        $("#material-group-modal-label").html("Add Group");
        $("#material-group-title").val("");
        $("#material-group-shown-on-calendar").prop("checked", false);

        $("#loading-material-group-modal").spin(false);
        $("#material-group-modal").modal("show");
    });

    $("[id^='edit-material-group-']").on("click", function () {
        helium.materials.edit_material_group_btn($(this));
    });

    $("[id^='delete-material-group-']").on("click", function () {
        helium.materials.delete_material_group_btn($(this));
    });

    // Material components
    $("#material-website").on("focusout", function () {
        var value = $(this).val();
        if (value !== "") {
            if (value.indexOf("http://") !== 0 && value.indexOf("https://") !== 0) {
                value = "http://" + value;
            }
            $(this).val(value);
        }
    });

    $("#material-modal").on("shown.bs.modal", function () {
        $("#material-title").focus();
    });

    $("#save-material").on("click", function () {
        helium.ajax_error_occurred = false;

        var material_title = $("#material-title").val(), data;

        helium.materials.clear_material_errors();

        // Validate
        if (/\S/.test(material_title)) {
            $("#loading-material-modal").spin(helium.SMALL_LOADING_OPTS);

            if ($("#material-group").val() === "") {
                data = {
                    "title": "Unnamed Group",
                    "shown_on_calendar": true
                };

                helium.materials.ajax_calls.push(helium.planner_api.add_material_group(function (data) {
                    helium.materials.add_material_group_to_page(data);

                    $("#material-group").val(data.id);
                }, data));
            }

            // If a course group was created, wait for that call to complete before proceeding
            $.when.apply(this, helium.materials.ajax_calls).done(function () {
                if (!helium.ajax_error_occurred) {
                    data = {
                        "title": material_title,
                        "status": $("#material-status").val(),
                        "condition": $("#material-condition").val(),
                        "website": $("#material-website").val(),
                        "price": $("#material-price").val(),
                        "details": $("#material-details").html(),
                        "seller_details": $("#material-seller-details").html(),
                        "material_group": $("#material-group").val()
                    };
                    if ($("#material-courses").val()) {
                        data["courses"] = $("#material-courses").val().toString();
                    }
                    if (helium.materials.edit) {
                        helium.planner_api.edit_material(function (data) {
                            if (helium.is_data_invalid(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-material-modal").spin(false);

                                if (helium.data_has_err_msg(data)) {
                                    $("#material-error").html(data.err_msg);
                                } else {
                                    $("#material-error").html("Oops, an unknown error has occurred. If the error persists, <a href=\"/support\">contact support</a>.");
                                }
                                $("#material-error").parent().show("fast");
                            } else {
                                var row_div = $("#material-" + data.id);
                                helium.materials.material_group_table[data.material_group].cell(row_div, 0).data(data.website !== "" ? "<a target=\"_blank\" href=\"" + data.website + "\">" + data.title + "</a>" : data.title);
                                helium.materials.material_group_table[data.material_group].cell(row_div, 1).data(data.price);
                                helium.materials.material_group_table[data.material_group].cell(row_div, 2).data(helium.MATERIAL_STATUS_CHOICES[data.status]);
                                helium.materials.material_group_table[data.material_group].cell(row_div, 3).data(helium.materials.get_course_names(data.courses));
                                helium.materials.material_group_table[data.material_group].cell(row_div, 4).data(helium.get_comments_with_link(data.details));
                                helium.materials.material_group_table[data.material_group].cell(row_div, 5).data(helium.get_comments_with_link(data.seller_details));
                                helium.materials.material_group_table[data.material_group].draw();
                                // Bind clickable attributes to their respective handlers
                                row_div.on("click", function () {
                                    helium.materials.edit_material_btn($(this).find("#edit-material-" + data.id));
                                });
                                row_div.find("#edit-material-" + data.id).on("click", function () {
                                    helium.materials.edit_material_btn($(this));
                                });
                                row_div.find("#delete-material-" + data.id).on("click", function (e) {
                                    e.stopPropagation();
                                    helium.materials.delete_material_btn($(this));
                                });

                                $("#loading-material-modal").spin(false);
                                $("#material-modal").modal("hide");
                            }
                        }, data["material_group"], helium.materials.edit_id, data);
                    } else {
                        helium.planner_api.add_material(function (data) {
                            if (helium.is_data_invalid(data)) {
                                helium.ajax_error_occurred = true;
                                $("#loading-material-modal").spin(false);

                                if (helium.data_has_err_msg(data)) {
                                    bootbox.alert(data[0].err_msg);
                                } else {
                                    bootbox.alert("Oops, an unknown error has occurred. If the error persists, <a href=\"/support\">contact support</a>.");
                                }
                            } else {
                                // Do not close the modal dialog until database saving is complete
                                $.when.apply(this, helium.materials.ajax_calls).done(function () {
                                    helium.materials.add_material_to_group(data, helium.materials.material_group_table[data.material_group]);
                                    helium.materials.material_group_table[data.material_group].draw();

                                    $("#loading-material-modal").spin(false);
                                    $("#material-modal").modal("hide");
                                });
                            }
                        }, data["material_group"], data);
                    }
                }
            });
        } else {
            // Validation failed, so don't save and prompt the user for action
            $("#material-error").html("You must specify values for fields highlighted in red.");
            $("#material-error").parent().show("fast");

            if (!/\S/.test(material_title)) {
                $("#material-title").parent().parent().addClass("has-error");
            }
        }
    });

    $("[id^='create-material-for-group-'], #no-materials-tab").on("click", function () {
        helium.materials.create_material_for_group_btn();
    });
}());