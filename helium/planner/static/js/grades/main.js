/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript functionality for persistence and the HeliumGrades object on the /planner/grades page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.1
 */

/**
 * Create the HeliumGrades persistence object.
 *
 * @constructor construct the HeliumClasses persistence object
 */
function HeliumGrades() {
    "use strict";

    this.ajax_calls = [];
    this.course_groups = null;
    this.courses_for_course_group = null;
    this.categories_for_course = null;
    this.grade_points_for_course_group = null;

    /*******************************************
     * Functions
     ******************************************/
    this.get_trend_arrow = function (trend) {
        return trend !== null ? (parseFloat(trend) > 0 ? " <span class=\"icon-x arrow-up-icon light-green\"></span>" : " <span class=\"icon-x arrow-down-icon light-red\"></span>") : "";
    };

    this.pie_hover = function (event, pos, item) {
        if (item) {
            $("#plot-tooltip").html(Math.round(item.datapoint[0]) + "%").css({
                top: pos.pageY - 25,
                left: pos.pageX + 5,
                "z-index": 100
            }).fadeIn("fast");
        } else {
            $("#plot-tooltip").hide();
        }
    };

    /**
     * Add the given course group's data to the page.
     *
     * @param data the data for the course group to be added
     */
    this.add_course_group_to_page = function (data) {
        if (helium.data_has_err_msg(data)) {
            helium.ajax_error_occurred = true;
            $("#loading-grades").spin(false);

            bootbox.alert(helium.get_error_msg(data));
        } else {
            $("#course-group-tabs").prepend('<li><a data-toggle="tab" href="#course-group-container-' + data.id + '"><i class="icon-book r-110"></i><span class="hidden-xs">' + data.title + (!data.shown_on_calendar ? " (H)" : "") + '</span></a></li>');
            var container = $('<div id="course-group-container-' + data.id + '" class="tab-pane"></div>');
            var details = $('<div id="details-for-course-group-' + data.id + '" class="col-sm-12 infobox-container">');
            container.append(details);
            $("#course-group-tab-content").append(container);

            var days_remaining = data.num_days - data.num_days_completed;
            if (days_remaining < 0) days_remaining = 0;
            var percent_thru = (data.num_days_completed / data.num_days) * 100;
            if (percent_thru > 100) percent_thru = 100;
            if (isNaN(percent_thru)) percent_thru = 0;
            var percent_completed = (data.num_homework_completed / data.num_homework) * 100;
            if (percent_completed > 100) percent_completed = 100;
            if (isNaN(percent_completed)) percent_completed = 0;

            details.append('<div class="infobox infobox-blue2">' + percent_thru.toFixed() + '<div class="infobox-progress"><div class="easy-pie-chart percentage easyPieChart" data-percent="' + percent_thru.toFixed() + '" data-size="46" style="width: 46px; height: 46px; line-height: 46px;"> <span class="percent">' + percent_thru.toFixed() + '</span>% <canvas width="46" height="46"></canvas></div></div><div class="infobox-data"><span class="infobox-text">thru term</span><div class="infobox-content">' + days_remaining + ' days remaining</div></div>');
            details.append('<div class="infobox infobox-red"><div class="infobox-icon"><i class="icon-beaker"></i></div><div class="infobox-data"><span class="infobox-data-number">' + data.num_homework + '</span><div class="infobox-content">assignments</div></div></div>');
            details.append('<div class="infobox infobox-red"><div class="infobox-icon"><i class="icon-beaker"></i></div><div class="infobox-data"><span class="infobox-data-number">' + data.num_homework_graded + '</span><div class="infobox-content">graded</div></div></div>');
            details.append('<div class="infobox infobox-blue2">' + percent_completed.toFixed() + '<div class="infobox-progress"><div class="easy-pie-chart percentage easyPieChart" data-percent="' + percent_completed.toFixed() + '" data-size="46" style="width: 46px; height: 46px; line-height: 46px;"><span class="percent">' + percent_completed.toFixed() + '</span>%<canvas width="46" height="46"></canvas></div></div><div class="infobox-data"><span class="infobox-text">' + data.num_homework_completed + ' complete</span><div class="infobox-content">' + (data.num_homework - data.num_homework_completed) + ' remaining</div></div></div><div class="space-20"></div></div>');
            container.append('<div class="row"><div class="col-xs-12"><div class="widget-box transparent"><div class="widget-header widget-header-flat"><h4 class="lighter"><i class="icon-signal"></i>Grades for ' + data.title + '</h4><a class="cursor-hover" data-action="collapse"><div class="widget-toolbar"><span class="badge badge-info">' + (parseFloat(data.average_grade) != -1 ? (parseFloat(data.average_grade).toFixed(2) + '% ' + (data.trend > 0 ? '<span class="icon-x arrow-up-icon light-green"></span>' : '<span class="icon-x arrow-down-icon light-red"></span>')) : 'N/A') + '</span><i class="icon-chevron-up"></i></div></a></div><div class="widget-body"><div class="widget-main"><div id="course-group-chart-' + data.id + '" style="width: 100%; height: 220px; padding: 0px; position: relative;"> <canvas class="flot-base" width="942" height="220" style="direction: ltr; position: absolute; left: 0px; top: 0px; width: 942px; height: 220px;"></canvas> <div class="flot-text" style="position: absolute; top: 0px; left: 0px; bottom: 0px; right: 0px; font-size: smaller; color: rgb(84, 84, 84);"><div class="flot-y-axis flot-y1-axis yAxis y1Axis" style="position: absolute; top: 0px; left: 0px; bottom: 0px; right: 0px; display: block;"><div class="flot-tick-label tickLabel" style="position: absolute; top: 190px; left: 7px; text-align: right;">50%</div><div class="flot-tick-label tickLabel" style="position: absolute; top: 152px; left: 7px; text-align: right;">60%</div><div class="flot-tick-label tickLabel" style="position: absolute; top: 114px; left: 7px; text-align: right;">70%</div><div class="flot-tick-label tickLabel" style="position: absolute; top: 76px; left: 7px; text-align: right;">80%</div><div class="flot-tick-label tickLabel"style="position: absolute; top: 38px; left: 7px; text-align: right;">90%</div><div class="flot-tick-label tickLabel"style="position: absolute; top: 0px; left: 1px; text-align: right;">100%</div></div></div><canvas class="flot-overlay" width="942" height="220" style="direction: ltr; position: absolute; left: 0px; top: 0px; width: 942px; height: 220px;"></canvas><div class="legend"><div style="position: absolute; width: 185px; height: 120px; top: 13px; right: 23px; opacity: 0.85; background-color: rgb(255, 255, 255);"></div><table style="position:absolute;top:13px;right:23px;;font-size:smaller;color:#545454"><tbody></tbody></table></div></div></div></div></div></div></div>');
            container.append('<div class="row"><div class="col-xs-12" id="course-group-piechart-' + data.id + '"></div></div>');
        }
    };
}

// Initialize HeliumGrades and give a reference to the Helium object
helium.grades = new HeliumGrades();

/*******************************************
 * jQuery initialization
 ******************************************/

$(document).ready(function () {
    "use strict";

    $("#loading-grades").spin(helium.SMALL_LOADING_OPTS);

    bootbox.setDefaults({
        locale: 'en'
    });

    /*******************************************
     * Other page initialization
     ******************************************/
    helium.planner_api.get_course_groups(function (data) {
        $.each(data, function (i, course_group_data) {
            helium.grades.add_course_group_to_page(course_group_data);
        });
    }, false);

    $($("#course-group-tabs li a").first()).tab("show");

    /*******************************************
     * Initialize component libraries
     ******************************************/
    $('.easy-pie-chart.percentage').each(function () {
        var $box = $(this).closest(".infobox"), barColor = $(this).data("color") || (!$box.hasClass("infobox-dark") ? $box.css("color") : "rgba(255,255,255,0.95)"), trackColor = barColor === "rgba(255,255,255,0.95)" ? "rgba(255,255,255,0.25)" : "#E2E2E2", size = parseInt($(this).data("size")) || 50;
        $(this).easyPieChart({
            barColor: barColor,
            trackColor: trackColor,
            scaleColor: false,
            lineCap: "butt",
            lineWidth: parseInt(size / 10),
            animate: /msie\s*(8|7|6)/.test(navigator.userAgent.toLowerCase()) ? false : 1000,
            size: size
        });
    });

    $(".sparkline").each(function () {
        var $box = $(this).closest(".infobox"), barColor = !$box.hasClass("infobox-dark") ? $box.css("color") : "#FFF";
        $(this).sparkline("html", {
            tagValuesAttribute: "data-values",
            type: "bar",
            barColor: barColor,
            chartRangeMin: $(this).data("min") || 0
        });
    });

    helium.planner_api.get_grades(function (data) {
        helium.ajax_error_occurred = false;
        if (helium.data_has_err_msg(data)) {
            helium.ajax_error_occurred = true;
            $("#loading-grades").spin(false);

            bootbox.alert(helium.get_error_msg(data));
        } else {
            helium.grades.course_groups = data.course_groups;
            helium.grades.courses_for_course_group = {};
            helium.grades.grade_points_for_course_group = {};
            helium.grades.categories_for_course = {};
            $.each(data.course_groups, function (i, course_group) {
                helium.grades.courses_for_course_group[course_group['id']] = course_group['courses'];

                helium.grades.grade_points_for_course_group[course_group['id']] = {};

                $.each(course_group['courses'], function (i, course) {
                    helium.grades.categories_for_course[course['id']] = course['categories'];
                    helium.grades.grade_points_for_course_group[course_group['id']][course['id']] = course['grade_points'];
                });
            });

            $('<div id="plot-tooltip"></div>').css({
                position: "absolute",
                display: "none",
                border: "1px solid #545454",
                padding: "2px",
                "background-color": "#fff",
                opacity: 0.90
            }).appendTo("body");

            // Build line graph for each course group
            $("div[id^='course-group-container-']").each(function () {
                var id = $(this).attr("id").split("course-group-container-")[1].split("_")[0], course_div, course_body_div, grade_distribution_string, weight_pie_div, grade_by_weight_pie_div, course_grade, category_table, category_table_body, chart_data_weight, chart_data_grade_by_weight, data_for_plot = [], i = 0, j = 0, course, course_grades, data_for_group = 0, data = [], category, course_list, group_plot_details = {
                    shadowSize: 0,
                    series: {
                        lines: {show: true},
                        points: {show: true}
                    },
                    xaxis: {
                        tickLength: 0,
                        mode: "time",
                        minTickSize: [1, "day"]
                    },
                    yaxis: {
                        ticks: 5,
                        min: 50,
                        max: 100,
                        tickFormatter: function (val, axis) {
                            return val + "%&nbsp;";
                        }
                    },
                    grid: {
                        backgroundColor: {colors: ["#fff", "#fff"]},
                        borderWidth: 1,
                        borderColor: "#555",
                        hoverable: true
                    }
                }, pie_chart_details = {
                    series: {
                        pie: {
                            show: true,
                            innerRadius: 0.2,
                            stroke: {
                                color: "#fff",
                                width: 2
                            }
                        }
                    },
                    legend: {
                        show: false
                    },
                    grid: {
                        hoverable: true
                    }
                };
                $("#course-group-chart-" + id).css({"width": "100%", "height": "220px"});
                course_list = $("#course-group-piechart-" + id);
                course_list.append("<div class=\"space-24\"></div>");

                if (helium.grades.courses_for_course_group[id].length > 0) {
                    for (i = 0; i < helium.grades.courses_for_course_group[id].length; i += 1) {
                        // Build data points for this course in the flot chart
                        course = helium.grades.courses_for_course_group[id][i];
                        course_grades = helium.grades.grade_points_for_course_group[id][course.id];

                        course_div = course_list.append("<div id=\"course-body-" + course.id + "\" class=\"widget-box collapsed\"><div class=\"widget-header widget-header-flat widget-header-small\"><h5><i class=\"icon-signal\"></i> <span>" + course.title + " </span></h5><a class=\"cursor-hover\" data-action=\"collapse\"><div class=\"widget-toolbar\"><span class=\"badge badge-info\">" + (parseFloat(course.overall_grade.toFixed(2)) !== -1 ? Math.round(course.overall_grade * 100) / 100 + "%" : "N/A") + helium.grades.get_trend_arrow(course.trend) + "</span> <i class=\"icon-chevron-down\"></i></div></a>");

                        data = [];
                        for (course_grade in course_grades) {
                            if (course_grades.hasOwnProperty(course_grade)) {
                                data.push([new Date(course_grades[course_grade][0]), course_grades[course_grade][1]]);
                                data_for_group += 1;
                            }
                        }

                        data_for_plot.push({label: "&nbsp;" + course.title, data: data, color: course.color});

                        // Build the course grading details div for this course
                        category_table = $("<table class=\"table table-striped table-bordered table-hover\"><thead><tr><th>Category</th><th class=\"hidden-xs\">Grades Recorded</th><th>Average Grade</th></tr></thead><tbody id=\"category-table-course-" + course.id + "\"></tbody></table>");
                        category_table_body = category_table.find("#category-table-course-" + course.id);

                        chart_data_weight = [];
                        chart_data_grade_by_weight = [];
                        for (j = 0; j < helium.grades.categories_for_course[course.id].length; j += 1) {
                            category = helium.grades.categories_for_course[course.id][j];
                            chart_data_weight.push({label: "", data: category.weight, color: category.color});
                            if (parseFloat(category.grade_by_weight) !== 0) {
                                chart_data_grade_by_weight.push({
                                    label: "",
                                    data: category.grade_by_weight,
                                    color: category.color
                                });
                            }

                            category_table_body.append("<tr><td><span class=\"label label-sm\" style=\"background-color: " + category.color + " !important\">" + category.title + "</span></td><td class=\"hidden-xs\">" + category.num_homework_graded + "</td><td>" + ((parseFloat(category.weight) !== 0 || !course.has_weighted_grading) ? (parseFloat(category.overall_grade.toFixed(2)) !== -1 ? "<span class=\"badge badge-info\">" + Math.round(category.overall_grade * 100) / 100 + "%" + helium.grades.get_trend_arrow(category.trend) + "</span>" : "N/A") : "Not Graded") + "</td></tr>");
                        }

                        if (helium.grades.categories_for_course[course.id].length > 0) {
                            grade_distribution_string = course.has_weighted_grading ? ("<div class=\"col-xs-12 col-sm-3\"><div class=\"row\"><h5>Weight Distribution</h5><hr /></div><div id=\"course-weight-piechart-" + course.id + "\"></div></div><div class=\"col-xs-12 col-sm-3\"><div class=\"row\"><h5>Current Grade Distribution</h5><hr /></div><div id=\"course-grade-by-weight-piechart-" + course.id + "\"></div></div>") : "";
                            course_body_div = course_div.find("#course-body-" + course.id).append("<div class=\"widget-body\"><div class=\"widget-main\">" + grade_distribution_string + "<div class=\"row\"><div class=\"col-xs-12 col-sm-" + (course.has_weighted_grading ? "6" : "12") + "\">" + $("<div />").append(category_table.clone()).html() + "</div><div class=\"col-xs-12 col-sm-4\"></div></div></div></div></div>");
                            weight_pie_div = course_body_div.find("#course-weight-piechart-" + course.id);
                            grade_by_weight_pie_div = course_body_div.find("#course-grade-by-weight-piechart-" + course.id);

                            if (course.has_weighted_grading) {
                                weight_pie_div.css({"width": "90%", "height": "100%", "min-height": "200px"});
                                grade_by_weight_pie_div.css({"width": "90%", "height": "100%", "min-height": "200px"});

                                $.plot(weight_pie_div, chart_data_weight, pie_chart_details);
                                $.plot(grade_by_weight_pie_div, chart_data_grade_by_weight, pie_chart_details);

                                weight_pie_div.bind("plothover", helium.grades.pie_hover);
                                grade_by_weight_pie_div.bind("plothover", helium.grades.pie_hover);
                            } else {
                                weight_pie_div.html("<div class=\"row\"><div class=\"col-sm-10 col-sm-offset-1 well\">This class does not have weighted grading. If you didn't expect this, head over to <a href=\"/planner/classes\">the classes page</a> and set weights for the categories!</div></div>");
                            }
                        } else {
                            course_div.find("#course-body-" + course.id).append("<div class=\"widget-body\"><div class=\"widget-main\"><div class=\"row\"><div class=\"col-xs-12 col-sm-10 col-sm-offset-1 well\">This class does not have any categories. If you don't expect this, head over to <a href=\"/planner/classes\">the classes page</a> and add categories to the class!</div></div></div></div>");
                        }
                    }

                    $.plot("#course-group-chart-" + id, data_for_plot, group_plot_details);

                    $("#course-group-chart-" + id).bind("plothover", function (event, pos, item) {
                        if (item) {
                            $("#plot-tooltip").html((Math.round(item.datapoint[1] * 100) / 100) + "%").css({
                                top: pos.pageY - 25,
                                left: pos.pageX + 5,
                                "z-index": 100
                            }).fadeIn("fast");
                        } else {
                            $("#plot-tooltip").hide();
                        }
                    });
                } else {
                    data_for_group = 0;
                }

                if (data_for_group === 0) {
                    $("#course-group-chart-" + id).parent().parent().parent().remove();
                    $("#details-for-course-group-" + id).after("<div class=\"row\"><div class=\"col-xs-12 col-sm-8 col-sm-offset-2 col-xs-12 well\">We can't calculate any grades for you if you don't have both <a href=\"/planner/classes\">classes</a> and <a href=\"/planner/calendar\">assignments</a>. Once you've entered these, head back here to check your grades!</div></div>");
                }
            });

            $("#loading-grades").spin(false);

            if ($("#course-group-tabs a").length === 0) {
                $("#no-grades-tab").addClass("active");
            }
        }
    });
});