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
var jobsTable;
var jobToDelete = null;
var jobsData;
var currentJobID = null;

var rewardChart;
var completeChart;

var best_episode = 0;
var best_eval_complete = 0;

var episodes_per_iteration = 20;

// global vars for calculating metric averages
var current_episode_number = 0;
var current_episode_training_count = 0;
var current_episode_training_reward_total = 0;
var current_episode_training_completion_total = 0;
var current_episode_eval_count = 0;
var current_episode_eval_reward_total = 0;
var current_episode_eval_completion_total = 0;
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
    $('#saveJobButton').click(function () {
        saveJob();
    });

    $('#startButton').click(function () {
        startTraining()
    });

    $('#stopButton').click(function () {
        stopTraining()
    });

    $('#addJobButton').click(function () {
        // jobsData.forEach(function (row) {
        //     if(row.status=="queued") {
        //
        //     }
        //     console.log(row.status);
        // });
        $.get("/pretrained_dirs")
            .done(function (data) {
                $("#pretrained_model").replaceOptions(data);
            });
        $("#id").val(null);
        $("#name").val("");
        $("#newJobModal").modal();
    });

    updateStatus();
    initJobTable();
    setTimeout(initRewardChart, 2000); // Delay 2s to let systemState update
    setInterval(updateStatus, 2000);
    setInterval(updateGraphs, 5000);
});

function setContainerStatus(element, status) {
    if (status=="running") {
        $("#"+element).removeClass("btn-secondary");
        $("#"+element).addClass("btn-success");
    } else {
        $("#"+element).addClass("btn-secondary");
        $("#"+element).removeClass("btn-success");
    }
}

function updateStatus() {
    var jqxhr = $.get("/current_job")
        .done(function (data) {
            // console.log("GET /current_job success");

            minioStatus = data['minio_status'];
            coachStatus = data['coach_status'];
            sagemakerStatus = data['sagemaker_status'];
            robomakerStatus = data['robomaker_status'];
            currentJobID = data['job_id'];
            $('#sessionIteration').html(data['iteration_number']);
            $('#sessionBestCheckpoint').html(data['best_checkpoint']);

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
    updateJobTable();
}

function saveJob() {
    console.log("in addNewJob()");
    data = {};
    $("form#newJobForm :input").each(function () {
        var input = $(this);
        data[input.attr('name')] = input.val();
    });

    data["change_start_position"] = $("#change_start_position").is(':checked');
    data["alternate_driving_direction"] = $("#alternate_driving_direction").is(':checked');
    data["randomize_obstacle_locations"] = $("#randomize_obstacle_locations").is(':checked');

    var jqxhr = $.post("/jobs", data)
        .done(function () {
            console.log("POST /jobs success");
            $("#newJobModal").modal('hide');
            updateJobTable();
        })
        .fail(function (error) {
            console.log("POST /jobs error");
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

function deleteJob(job_id, confirmed = false) {
    if (confirmed) {
        console.log("Deleting job " + job_id);
        $('#deleteJobModal').modal('hide');
        $.ajax({
            url: '/job/' + job_id,
            type: 'DELETE',
            success: function (result) {
                console.log(result);
                updateJobTable();
            }
        });

    } else {

        $('#deleteJobButton').click(function () {
            deleteJob(job_id, confirmed = true);
        });

        $('#deleteJobModal').modal();
    }
}


function initJobTable() {
    var columns = [
        {title: "Job Name", field: "name", sorter: "string"},
        {title: "Target Episodes", field: "episodes", sorter: "number", align: "center"},
        {title: "Track", field: "track", sorter: "string", align: "center"},
        {title: "Status", field: "status", formatter: "string", align: "center"},
        {title: "Episodes trained", field: "episodes_trained", formatter: "string", align: "center"},
        {title: "Laps complete", field: "laps_complete", sorter: "number", align: "center"},
        {title: "Fastest lap", field: "best_lap_time", sorter: "number", align: "center"},
        {
            formatter: editIcon, width: 40, align: "center", cellClick: function (e, cell) {
                editJob(cell.getRow().getData().id)
            }
        },
        {
            formatter: delIcon, width: 40, align: "center", cellClick: function (e, cell) {
                deleteJob(cell.getRow().getData().id)
            }
        }
    ];
    let url = "/jobs";
    jobsTable = new Tabulator("#jobsTable", {
        columns: columns,
        layout: "fitColumns",
        height: "150"
        // ajaxURL: url
    });
    updateJobTable();
}


function updateJobTable() {
    $.get("/jobs")
        .done(function (data) {
            // console.log("GET /jobs success");
            if (jobsTable) {
                jobsTable.replaceData(data);
                jobsData = data;
            } else {
                console.log("No table");
            }

        })
        .fail(function () {
            console.log("GET /jobs error");
        });
}


function editJob(job_id) {
    // job_id = item.currentTarget.dataset["id"];
    console.log(job_id);
    $.get("/job/" + job_id)
        .done(function (data) {
            console.log(data);
            for (var key in data) {
                $("#" + key).val(data[key]);
            }
            $("#newJobModal").modal();

        })
        .fail(function () {
            console.log("GET /job error");
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
    completeChart.series[3].data = [];


    setTimeout(startVideo, 5000);
    initRewardChart();
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
    if (currentJobID == null) {
        // console.log("No training job ID yet")
        return 0;
    }
    footer("Fetching metrics since episode "+lastMetricsEpisode);
    // console.log("Starting data update from episode " + lastMetricsEpisode);
    $.get("/metrics/" + currentJobID + "?from_episode=" + lastMetricsEpisode)
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

                iteration = parseInt(current_episode_number / episodes_per_iteration) + 1;

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
                            console.log("Best now " + best_eval_complete + " at episode "+ current_episode_number);
                            new_best_episode = current_episode_number;
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
                console.log("Plotlines: "+rewardChart.xAxis[0].plotLines());
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
                $('#sessionEpisode').html(episode);
                $('#sessionPhase').html(phase);

            }


        })
        .fail(function () {
            footer("ERROR: Failed to fetch metrics");
            console.log("GET /metrics error");
        });
}

function initRewardChart() {
    console.log("initRewardChart()");
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
            }
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
            }
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

    footer("Fetching metrics since episode "+lastMetricsEpisode);
    $.ajax({
        url: "/metrics/" + currentJobID + "?from_episode=" + lastMetricsEpisode,
        success: function (data) {
            var training_reward_data = [];
            var training_completion_data = [];
            var eval_reward_data = [];
            var eval_completion_data = [];
            var complete_eval_times = [];
            var complete_eval_reward = [];
            var complete_training_times = [];
            var complete_training_reward = [];

            footer("Processing metrics...");
            data.forEach(function (metric) {
                current_episode_number = metric["episode"];
                lastMetricsEpisode = current_episode_number;
                // iteration = metric["trial"];
                iteration = parseInt(current_episode_number / episodes_per_iteration) + 1;
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
                        eval_completion_data.push([current_episode_number, eval_average_completion]);

                        if (eval_average_completion > best_eval_complete) {
                            best_eval_complete = eval_average_completion;
                            console.log("Best now " + best_eval_complete + " at episode "+ current_episode_number);
                            best_episode = current_episode_number;
                        }
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
                    }
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

            rewardChart = new Highcharts.Chart('rewardChart', rewardOptions);
            completeChart = new Highcharts.Chart('completeChart', completeOptions);

            rewardChart.xAxis[0].addPlotLine({
                value: best_episode,
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
    console.log("Setting footer to "+msg);
    $("#footer").text("Status: "+msg);
}