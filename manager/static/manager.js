var systemState;
var targetState;
var minioStatus;
var coachStatus;
var sagemakerStatus;
var robomakerStatus;
var previousRobomakerStatus = null;
var metrics;
var rewardGraph;
var completionGraph;
var lastMetricsEpisode = 0;
// var lastPhase = null;
var modelsTable;
var jobToDelete = null;
var modelsData;
var currentModelID = null;

var rewardChart;
var completeChart;
var statusChart;
var entropyChart;
var currentChart = null;

var best_episode = 0;
var best_eval_complete = 0;

var episodesPerIteration = 20;

// global vars for calculating metric averages
var current_episode_number = 0;
var current_episode_training_count = 0;
var current_episode_training_reward_total = 0;
var current_episode_training_completion_total = 0;
var current_episode_eval_count = 0;
var current_episode_eval_reward_total = 0;
var current_episode_eval_completion_total = 0;
var current_episode_eval_complete_count = 0;
var current_episode_eval_offtrack_count = 0;
var current_episode_eval_crashed_count = 0;
var current_episode_eval_reversed_count = 0;

var previous_phase = null;


(function ($, window) {
    $.fn.replaceOptions = function (options) {
        var self, $option;

        this.empty();
        self = this;

        $.each(options, function (index, option) {
            $option = $("<option></option>")
                .attr("value", option.value)
                .text(option.text);
            self.append($option);
        });
    };
})(jQuery, window);


$(document).ready(function () {

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

    $('#saveModelButton').click(function () {
        saveModel();
    });

    $('#startButton').click(function () {
        startTraining()
    });

    $('#stopButton').click(function () {
        stopTraining()
    });

    $('#addModelButton').click(function () {

        $.get("/pretrained_dirs")
            .done(function (data) {
                $("#pretrained_model").replaceOptions(data);
            });
        $("#id").val(null);
        $("#name").val("");
        $("#newModelModal").modal();
    });

    updateStatus();
    initModelsTable();
    setTimeout(initCharts, 2000); // Delay 2s to let systemState update
    setInterval(updateStatus, 2000);
    setInterval(updateGraphs, 5000);
});

function setContainerStatus(element, status) {
    if (status == "running") {
        $("#" + element).removeClass("btn-secondary");
        $("#" + element).addClass("btn-success");
    } else {
        $("#" + element).addClass("btn-secondary");
        $("#" + element).removeClass("btn-success");
    }
}

function updateStatus() {
    var jqxhr = $.get("/current_job")
        .done(function (data) {
            // console.log("GET /current_job success");
            // console.log(data);

            minioStatus = data['minio_status'];
            coachStatus = data['coach_status'];
            sagemakerStatus = data['sagemaker_status'];
            robomakerStatus = data['robomaker_status'];
            currentModelID = data['model_id'];
            episodesPerIteration = data["episodes_per_iteration"];

            $('#sessionEpisode').html(data['episode_number']);
            $('#sessionIteration').html(data['iteration_number']);
            // $('#sessionBestCheckpoint').html(data['best_checkpoint']);

            if (coachStatus && sagemakerStatus && robomakerStatus) {
                systemState = "running";
                $('#sessionState').html("Running");
                $('#startButton').prop('disabled', true);
                $('#stopButton').prop('disabled', false);
                if (robomakerStatus != previousRobomakerStatus) {
                    startVideo();
                }
                // initRewardChart();
            } else if (coachStatus || sagemakerStatus || robomakerStatus) {
                $('#startButton').prop('disabled', false);
                $('#stopButton').prop('disabled', false);
                if (targetState == "running") {
                    $('#sessionState').html("Starting");
                } else if (targetState == "stopped") {
                    $('#sessionState').html("Stopping");
                }

                systemState = "partial";
                // $('#sessionState').html("partial");


            } else {
                systemState = "stopped";
                if (targetState == "stopped") $('#sessionState').html("Stopped");
                $('#startButton').prop('disabled', false);
                $('#stopButton').prop('disabled', true);
            }

            setContainerStatus("minioStatus", minioStatus);
            setContainerStatus("coachStatus", coachStatus);
            setContainerStatus("robomakerStatus", robomakerStatus);
            setContainerStatus("sagemakerStatus", sagemakerStatus);
            previousRobomakerStatus = robomakerStatus;

        })
        .fail(function () {
            console.log("GET /current_job error");
        });
    updateModelsTable();
}

function saveModel() {
    data = {};
    $("form#newModelForm :input").each(function () {
        var input = $(this);
        data[input.attr('name')] = input.val();
    });

    data["change_start_position"] = $("#change_start_position").is(':checked');
    data["alternate_driving_direction"] = $("#alternate_driving_direction").is(':checked');
    data["randomize_obstacle_locations"] = $("#randomize_obstacle_locations").is(':checked');

    var jqxhr = $.post("/models", data)
        .done(function () {
            console.log("POST /models success");
            $("#newModelModal").modal('hide');
            updateModelsTable();
        })
        .fail(function (error) {
            console.log("POST /models error");
            console.log(error['responseText']);
            $("#formError").html(error['responseText']);
        })
}

var editIcon = function (cell, formatterParams, onRendered) { //plain text value
    return "<i class='fa fa-edit'></i>";
};

var delIcon = function (cell, formatterParams, onRendered) { //plain text value
    return "<i class='fa fa-trash-alt'></i>";
};

function deleteModel(model_id, confirmed = false) {
    if (confirmed) {
        console.log("Deleting model " + model_id);
        $('#deleteModelModal').modal('hide');
        $.ajax({
            url: '/model/' + model_id,
            type: 'DELETE',
            success: function (result) {
                console.log(result);
                updateModelsTable();
            }
        });

    } else {

        $('#deleteModelButton').click(function () {
            deleteModel(model_id, confirmed = true);
        });

        $('#deleteModelModal').modal();
    }
}


function initModelsTable() {
    var columns = [
        {title: "ID", field: "id", sorter: "number", width: 50, responsive: 1},
        {title: "Model Name", field: "name", sorter: "string", responsive: 0},
        {title: "Description", field: "description", sorter: "string", responsive: 2},
        {title: "Status", field: "status", formatter: "plaintext", align: "center", responsive: 0},
        {title: "Target Episodes", field: "episodes_target", sorter: "number", align: "center"},
        {title: "Episodes trained", field: "episodes_trained", formatter: "plaintext", align: "center", responsive: 1},
        {title: "Laps complete", field: "laps_complete", sorter: "number", align: "center", responsive: 1},
        {title: "Fastest lap", field: "best_lap_time", sorter: "number", align: "center", responsive: 1},
        {
            formatter: editIcon, width: 40, align: "center", cellClick: function (e, cell) {
                editModel(cell.getRow().getData().id)
            }, responsive: 0
        },
        {
            formatter: delIcon, width: 40, align: "center", cellClick: function (e, cell) {
                deleteModel(cell.getRow().getData().id)
            }, responsive: 0
        }
    ];
    let url = "/models";
    modelsTable = new Tabulator("#modelsTable", {
        columns: columns,
        layout: "fitColumns",
        responsiveLayout: "hide",
        height: "150",
        rowClick: function (e, row) {
            model_id = row.getCell("id").getValue();
            model_name = row.getCell("name").getValue();
            initCharts(row.getCell("id").getValue());
        }
    });
    updateModelsTable();
}


function updateModelsTable() {
    $.get("/models")
        .done(function (data) {
            if (modelsTable) {
                modelsTable.replaceData(data);
                modelsData = data;
            } else {
                console.log("No table");
            }

        })
        .fail(function () {
            console.log("GET /models error");
        });
}


function editModel(model_id) {
    $.get("/model/" + model_id)
        .done(function (data) {
            for (var key in data) {
                $("#" + key).val(data[key]);
                console.log(key + " = ["+data[key]+"]");
                if ($("#" + key).is(':checkbox')) {
                    console.log("is checkbox");
                    if (data[key] == true) {
                        console.log("Setting checked");
                        $("#" + key).attr('checked', true);
                    } else {
                        $("#" + key).attr('checked', false);
                    }
                }
            }
            $("#newModelModal").modal();

        })
        .fail(function () {
            console.log("GET /model error");
        });
}

function startTraining() {
    console.log("Clicked start");

    targetState = "running";
    var data = {
        'action': 'start_training'
    };

    $.ajax({
        type: "POST",
        url: '/current_job',
        dataType: 'application/json',
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        success: function () {
            console.log("POST /current_job success");
        }
    });

    rewardChart.series[0].data = [];
    rewardChart.series[1].data = [];
    rewardChart.series[2].data = [];
    completeChart.series[0].data = [];
    completeChart.series[1].data = [];
    completeChart.series[2].data = [];

    currentModelID = null;

    setTimeout(startVideo, 5000);
    initCharts();
}

function stopTraining() {
    console.log("Clicked stop");

    targetState = "stopped";
    var data = {
        action: "stop_training"
    };

    $.ajax({
        type: "POST",
        url: '/current_job',
        dataType: 'application/json',
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        success: function () {
            console.log("POST /current_job success");
            $("#videoImg").attr("src", "/static/nosignal.png");
        }
    });

}

function startVideo() {
    video_url = "http://" + window.location.hostname + ":8080/stream?topic=/racecar/deepracer/kvs_stream";
    $("#videoImg").attr("src", video_url);
    $("#videoImg").bind("error", function () {
        console.log("video error");
        $("#videoImg").unbind();
        $("#videoImg").attr("src", "/static/nosignal.png");
        setTimeout(startVideo, 3000)
    });
}

function getNewMetrics() {
    var jqxhr = $.get("/metrics?from_episode=" + lastMetricsEpisode)
        .done(function (data) {
            console.log("GET /metrics success");
            // console.log(data);
            // data.forEach(addJobRow);
            return (data)
        })
        .fail(function () {
            console.log("GET /metrics error");
        });
}

function updateGraphs() {
    if (systemState != "running") {
        // console.log("Not running yet so not updating graphs");
        return 0;
    }
    if (currentModelID == null) {
        // console.log("No training job ID yet")
        return 0;
    }


    // Don't update graphs unless we're showing the graphs for a model currently being trained
    if (currentChart != currentModelID) {
        return 0;
    }
    footer("Fetching metrics since episode " + lastMetricsEpisode);
    // console.log("Starting data update from episode " + lastMetricsEpisode);
    $.get("/metrics/" + currentModelID + "?from_episode=" + lastMetricsEpisode)
        .done(function (data) {
            let episode = 0;
            let phase = null;
            let new_best_episode = 0;
            // console.log("Got " + data.length + " metrics");
            footer("Processing metrics...");
            data.forEach(function (metric) {
                // console.log(metric);
                phase = metric["phase"];
                // iteration = metric["trial"];

                current_episode_number = metric["episode"];
                lastMetricsEpisode = current_episode_number;

                iteration = parseInt(current_episode_number / episodesPerIteration) + 1;

                // console.log("1: "+ current_episode_number % 30);
                // var iteration = current_episode_number % episodes_per_iteration;
                // iteration += 1;

                if (phase == "training") {
                    if (previous_phase == "evaluation") {
                        current_episode_training_count = 0;
                        current_episode_training_completion_total = 0;
                        current_episode_training_reward_total = 0;

                        var eval_average_reward = current_episode_eval_reward_total / current_episode_eval_count;
                        var eval_average_completion = current_episode_eval_completion_total / current_episode_eval_count;

                        console.log("adding eval_completion datapoint for episode=" + current_episode_number + " value=" + eval_average_completion);
                        rewardChart.series[1].addPoint([current_episode_number - 1, eval_average_completion]);

                        if (eval_average_completion > best_eval_complete) {
                            best_eval_complete = eval_average_completion;
                            console.log("Best now " + best_eval_complete + " at episode " + current_episode_number - 1);
                            new_best_episode = current_episode_number - 1;
                            // TODO: plotLine
                        }


                    }
                    current_episode_training_count += 1;
                    current_episode_training_completion_total += metric["completion_percentage"];
                    current_episode_training_reward_total += metric["reward_score"];
                    // console.log("Training iteration " + iteration + ": count=" + current_episode_training_count + " pc_total=" + current_episode_training_completion_total + " reward_total=" + current_episode_training_reward_total);

                    if (metric["episode_status"] == "Lap complete") {
                        completeChart.series[0].addPoint([current_episode_number, metric["elapsed_time_in_milliseconds"] / 1000]);
                        completeChart.series[1].addPoint([current_episode_number, metric["reward_score"]]);
                    }

                    previous_phase = "training";
                }
                if (phase == "evaluation") {
                    if (previous_phase == "training") {
                        current_episode_eval_count = 0;
                        current_episode_eval_reward_total = 0;
                        current_episode_eval_completion_total = 0;

                        var training_average_reward = current_episode_training_reward_total / current_episode_training_count;
                        var training_average_completion = current_episode_training_completion_total / current_episode_training_count;

                        console.log("adding training_completion datapoint for episode=" + current_episode_number + " value=" + training_average_completion);
                        console.log("adding training_reward datapoint for episode=" + current_episode_number + " value=" + training_average_reward);
                        rewardChart.series[0].addPoint([current_episode_number, training_average_completion]);
                        rewardChart.series[2].addPoint([current_episode_number, training_average_reward]);

                    }
                    current_episode_eval_count += 1;
                    current_episode_eval_completion_total += metric["completion_percentage"];
                    current_episode_eval_reward_total += metric["reward_score"];
                    // console.log("Evaluation iteration " + iteration + ": count=" + current_episode_eval_count + " pc_total=" + current_episode_eval_completion_total);

                    if (metric["episode_status"] == "Lap complete") {
                        completeChart.series[2].addPoint([current_episode_number, metric["elapsed_time_in_milliseconds"] / 1000]);
                        completeChart.series[3].addPoint([current_episode_number, metric["reward_score"]]);
                    }

                    previous_phase = "evaluation";
                }
            });

            if (new_best_episode > best_episode) {
                best_episode = new_best_episode;
                console.log("Plotlines: " + rewardChart.xAxis[0].plotLines);
                console.log("Adding new best plotline at episode " + best_episode);
                rewardChart.xAxis[0].removePlotLine("best");
                rewardChart.xAxis[0].addPlotLine({
                    value: best_episode,
                    color: 'grey',
                    dashStyle: "ShortDash",
                    id: 'best',
                    zIndex: 1,
                    label: {text: 'Best model', style: {color: "grey"}}
                });
            }
            footer("");

            if (phase) {
                // $('#sessionEpisode').html(episode);
                $('#sessionPhase').html(phase);

            }


        })
        .fail(function () {
            footer("ERROR: Failed to fetch metrics");
            console.log("GET /metrics error");
        });
}

function initCharts(model_id = null) {
    if (model_id == null) {
        model_id = currentModelID;
    }
    console.log("initRewardChart() for model_id=" + model_id);
    currentChart = model_id;
    var rewardOptions = {
        chart: {
            type: 'line',
            height: "75%"
        },
        title: {
            text: 'Training metrics'
        },
        xAxis: {
            title: {
                text: 'Episode'
            },
            min: 0
        },
        yAxis: [{ // Primary yAxis
            labels: {
                style: {
                    color: "#1d8102"
                }
            },
            title: {
                text: 'Reward',
            }


        }, { // Secondary yAxis
            gridLineWidth: 0,
            title: {
                text: 'Percentage lap complete',
            },
            max: 100,
            opposite: true,
        }],
        series: [{
            name: 'Training % lap complete',
            color: "#0073bb",
            yAxis: 1,
            data: []
        }, {
            name: 'Evaluation % lap complete',
            data: [],
            yAxis: 1,
            color: "#FF0000"
        }, {
            name: 'Average reward',
            data: [],
            yAxis: 0,
            color: "#1d8102"
        }]
    };

    var completeOptions = {
        chart: {
            height: "75%"
        },
        title: {
            text: 'Complete laps'
        },
        xAxis: {
            title: {
                text: 'Episode'
            },
            min: 0
        },
        yAxis: [{ // Primary yAxis
            labels: {
                style: {
                    color: "#1d8102"
                }
            },
            title: {
                text: 'Reward',
            }


        }, { // Secondary yAxis
            gridLineWidth: 0,
            title: {
                text: 'Lap time (seconds)',
            },
            opposite: true,
        }],
        series: [{
            name: 'Training lap time',
            color: "#0073bb",
            yAxis: 1,
            data: [],
            type: "line"
        }, {
            name: 'Training reward',
            data: [],
            yAxis: 0,
            color: "#1d8102",
            type: "line"
        }, {
            name: 'Eval lap time',
            color: "#AA0000",
            yAxis: 1,
            data: [],
            type: "line"
        }]
    };

    var statusOptions = {
        chart: {
            height: "75%",
            type: "line"
        },
        title: {
            text: 'Lap status'
        },
        xAxis: {
            title: {
                text: 'Episode'
            },
            min: 0
        },
        yAxis: [{
            labels: {
                style: {
                    color: "#1d8102"
                }
            },
            title: {
                text: '% of eval laps',
            }
        }],
        plotOptions: {
            column: {
                stacking: 'percent'
            }
        },
        series: [{
            name: 'Lap complete',
            color: "#1d8102",
            data: [],
        }, {
            name: 'Off track',
            data: [],
            color: "#ffc502",
        }, {
            name: 'Crashed',
            color: "#AA0000",
            data: []
        }, {
            name: 'Reversed',
            color: "#00a29f",
            data: []
        }
        ]
    };

    var entropyOptions = {
        chart: {
            height: "75%",
            type: "line"
        },
        title: {
            text: 'Entropy'
        },
        xAxis: {
            title: {
                text: 'Episode'
            },
            min: 0
        },
        yAxis: [{
            labels: {
                style: {
                    color: "#1d8102"
                }
            },
            title: {
                text: 'Entropy',
            }
        }],
        series: [{
            name: 'Entropy',
            color: "#182ac4",
            data: [],
        }
        ]
    };


    footer("Fetching all metrics for model ID " + model_id);
    // let url = "/metrics/" + currentModelID + "?from_episode=" + lastMetricsEpisode;

    let url = "/metrics/" + model_id;
    console.log(url);
    $.ajax({
        url: url,
        success: function (data) {
            var training_reward_data = [];
            var training_completion_data = [];
            var eval_reward_data = [];
            var eval_completion_data = [];
            var complete_eval_times = [];
            var complete_eval_reward = [];
            var complete_training_times = [];
            var complete_training_reward = [];
            var complete_avg_data = [];
            var offtrack_avg_data = [];
            var crashed_avg_data = [];
            var reversed_avg_data = [];
            console.log("got " + data.length + " metrics");
            footer("Processing metrics...");
            data.forEach(function (metric) {
                current_episode_number = metric["episode"];
                lastMetricsEpisode = current_episode_number;
                // iteration = metric["trial"];
                iteration = parseInt(current_episode_number / episodesPerIteration) + 1;
                // var iteration = current_episode_number % episodes_per_iteration;
                // iteration += 1;

                if (metric["phase"] == "training") {
                    if (previous_phase == "evaluation") {
                        current_episode_training_count = 0;
                        current_episode_training_completion_total = 0;
                        current_episode_training_reward_total = 0;

                        var eval_average_reward = current_episode_eval_reward_total / current_episode_eval_count;
                        var eval_average_completion = current_episode_eval_completion_total / current_episode_eval_count;

                        // eval_reward_data.push([current_episode_number, eval_average_reward]);
                        eval_completion_data.push([current_episode_number - 1, eval_average_completion]);

                        if (eval_average_completion > best_eval_complete) {
                            best_eval_complete = eval_average_completion;
                            console.log("Best now " + best_eval_complete + " at episode " + (current_episode_number - 1));
                            best_episode = current_episode_number - 1;
                        }

                        let complete_avg = (current_episode_eval_complete_count/current_episode_eval_count)*100;
                        let offtrack_avg = (current_episode_eval_offtrack_count/current_episode_eval_count)*100;
                        let crashed_avg = (current_episode_eval_crashed_count/current_episode_eval_count)*100;
                        let reversed_avg = (current_episode_eval_reversed_count/current_episode_eval_count)*100;
                        complete_avg_data.push([current_episode_number - 1, complete_avg]);
                        offtrack_avg_data.push([current_episode_number - 1, offtrack_avg]);
                        crashed_avg_data.push([current_episode_number - 1, crashed_avg]);
                        reversed_avg_data.push([current_episode_number - 1, reversed_avg]);

                    }
                    current_episode_training_count += 1;
                    current_episode_training_completion_total += metric["completion_percentage"];
                    current_episode_training_reward_total += metric["reward_score"];
                    previous_phase = "training";
                }
                if (metric["phase"] == "evaluation") {
                    if (previous_phase == "training") {
                        current_episode_eval_count = 0;
                        current_episode_eval_reward_total = 0;
                        current_episode_eval_completion_total = 0;
                        current_episode_eval_complete_count = 0;
                        current_episode_eval_crashed_count = 0;
                        current_episode_eval_offtrack_count = 0;
                        current_episode_eval_reversed_count = 0;

                        var training_average_reward = current_episode_training_reward_total / current_episode_training_count;
                        var training_average_completion = current_episode_training_completion_total / current_episode_training_count;

                        training_reward_data.push([current_episode_number, training_average_reward]);
                        training_completion_data.push([current_episode_number, training_average_completion]);

                    }
                    current_episode_eval_count += 1;
                    current_episode_eval_completion_total += metric["completion_percentage"];
                    current_episode_eval_reward_total += metric["reward_score"];
                    previous_phase = "evaluation";
                }

                if (metric["episode_status"] == "Lap complete") {
                    if (metric["phase"] == "training") {
                        complete_training_times.push([current_episode_number, metric["elapsed_time_in_milliseconds"] / 1000]);
                        complete_training_reward.push([current_episode_number, metric["reward_score"]]);
                    }
                    if (metric["phase"] == "evaluation") {
                        complete_eval_times.push([current_episode_number, metric["elapsed_time_in_milliseconds"] / 1000]);
                        complete_eval_reward.push([current_episode_number, metric["reward_score"]]);
                        current_episode_eval_complete_count += 1;
                    }
                }

                if (metric["episode_status"] == "Off track" && metric["phase"] == "evaluation") {
                    current_episode_eval_offtrack_count += 1;
                }

                if (metric["episode_status"] == "Crashed" && metric["phase"] == "evaluation") {
                    current_episode_eval_crashed_count += 1;
                }

                if (metric["episode_status"] == "Reversed" && metric["phase"] == "evaluation") {
                    current_episode_eval_reversed_count += 1;
                }
            });

            // console.log(JSON.stringify(eval_data));
            // console.log(JSON.stringify(reward_data));
            rewardOptions.series[0].data = training_completion_data;
            rewardOptions.series[1].data = eval_completion_data;
            rewardOptions.series[2].data = training_reward_data;

            completeOptions.series[0].data = complete_training_times;
            completeOptions.series[1].data = complete_training_reward;
            completeOptions.series[2].data = complete_eval_times;
            // completeOptions.series[3].data = complete_eval_reward;

            statusOptions.series[0].data = complete_avg_data;
            statusOptions.series[1].data = offtrack_avg_data;
            statusOptions.series[2].data = crashed_avg_data;
            statusOptions.series[3].data = reversed_avg_data;

            rewardChart = new Highcharts.Chart('rewardChart', rewardOptions);
            completeChart = new Highcharts.Chart('completeChart', completeOptions);
            statusChart = new Highcharts.Chart('statusChart', statusOptions);
            entropyChart = new Highcharts.Chart('entropyChart', entropyOptions);

            rewardChart.xAxis[0].addPlotLine({
                value: best_episode - 1,
                color: 'grey',
                dashStyle: "ShortDash",
                id: 'best',
                zIndex: 1,
                label: {text: 'Best model', style: {color: "grey"}}
            });
            footer("");

            // setTimeout(setBest, 1000);
        }
    });
}

function footer(msg) {
    $("#footer").text("Status: " + msg);
}