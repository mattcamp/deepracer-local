var systemState;
var targetState;
var minioStatus;
var coachStatus;
var sagemakerStatus;
var robomakerStatus;
var metrics;
var rewardGraph;
var completionGraph;
var lastMetricsEpisode = 0;
var lastPhase = null;
var jobsTable;


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
        $("#id").val(null);
        $("#name").val("");
        $("#newJobModal").modal();
    });

    updateStatus();
    initJobTable();
    setTimeout(initGraphs, 2000); // Delay 2s to let systemState update
    setInterval(updateStatus, 2000);
});

function updateStatus() {
    var jqxhr = $.get("/current_job")
        .done(function (data) {
            // console.log("GET /current_job success");

            minioStatus = data['minio_status'];
            coachStatus = data['coach_status'];
            sagemakerStatus = data['sagemaker_status'];
            robomakerStatus = data['robomaker_status'];
            $('#sessionIteration').html(data['iteration_number']);
            $('#sessionBestCheckpoint').html(data['best_checkpoint']);

            if (coachStatus && sagemakerStatus && robomakerStatus) {
                systemState = "running";
                $('#sessionState').html("Running");
                $('#startButton').prop('disabled', true);
                $('#stopButton').prop('disabled', false);
            } else if (coachStatus || sagemakerStatus || robomakerStatus) {
                $('#startButton').prop('disabled', false);
                $('#stopButton').prop('disabled', false);
                if (targetState == "running") {
                    $('#sessionState').html("Starting");
                } else if (targetState == "stopped") {
                    $('#sessionState').html("Stopping");
                }

                systemState = "partial";
                $('#sessionState').html("partial");


            } else {
                systemState = "stopped";
                if (targetState == "stopped") $('#sessionState').html("Stopped");
                $('#startButton').prop('disabled', false);
                $('#stopButton').prop('disabled', true);
            }

            $("#minioStatus").text(minioStatus);
            $("#coachStatus").html(coachStatus);
            $("#sagemakerStatus").html(sagemakerStatus);
            $("#robomakerStatus").html(robomakerStatus);

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

var editIcon = function(cell, formatterParams, onRendered){ //plain text value
    return "<i class='fa fa-edit'></i>";
};

var delIcon = function(cell, formatterParams, onRendered){ //plain text value
    return "<i class='fa fa-trash-alt'></i>";
};

function initJobTable() {
    var columns = [
        {title:"Job Name", field:"name", sorter:"string"},
        {title:"Episodes", field:"episodes", sorter:"number", align:"center"},
        {title:"Track", field:"track", sorter:"string", align: "center"},
        {title:"Status", field:"status", formatter:"string", align:"center"},
        {title:"Laps complete", field:"laps_complete", sorter:"number", align: "center"},
        {title:"% laps complete", field:"average_pct_complete", sorter:"number", align:"center"},
        {title:"Fastest lap", field:"best_lap_time", sorter:"number", align:"center"},
        {formatter:editIcon, width:40, align:"center", cellClick:function(e, cell){editJob(cell.getRow().getData().id)}},
        {formatter:delIcon, width:40, align:"center", cellClick:function(e, cell){alert("Printing row data for: " + cell.getRow().getData().name)}}
    ];
    let url = "/jobs";
    jobsTable = new Tabulator("#jobsTable", {
        columns: columns,
        layout:"fitColumns",
        height: "150"
        // ajaxURL: url
    });
    updateJobTable();
}


function updateJobTable() {
    $.get("/jobs")
        .done(function (data) {
            console.log("GET /jobs success");
            if(jobsTable) {
                jobsTable.replaceData(data)
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
    $.get("/job?job_id=" + job_id)
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
    setTimeout(startVideo, 5000);
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
        }
    });

}

function startVideo() {
    $("#videoImg").attr("src", "http://127.0.0.1:8080/stream?topic=/racecar/deepracer/kvs_stream");
    $("#videoImg").bind("error", function () {
        console.log("video error");
        $("#videoImg").attr("src", "/static/nosignal.png");
        setTimeout(startVideo, 3000)
    });
}

function getNewMetrics() {
    var jqxhr = $.get("/metrics?from_episode=" + lastMetricsEpisode)
        .done(function (data) {
            console.log("GET /metrics success");
            console.log(data);
            // data.forEach(addJobRow);
            return (data)
        })
        .fail(function () {
            console.log("GET /metrics error");
        });
}

function initGraphs() {
    console.log("initGraphs()");
    rewardGraphCanvas = document.getElementById('rewardGraph');
    completionGraphCanvas = document.getElementById('completionGraph');

    rewardGraphData = {
        labels: [],
        datasets: [{
            label: 'Eval',
            data: [],
            backgroundColor: [
                'rgba(255, 99, 132, 0.8)'
            ],
            borderColor: 'rgba(255, 99, 132, 1)',
            pointBorderWidth: 0,
            pointRadius: 3,
            // pointBorderColor: 'rgba(255, 0, 0, 1)',
            borderWidth: 1,
            spanGaps: true,
            fill: false
        },
            {
                label: 'Training',
                data: [],
                backgroundColor: [
                    'rgba(0, 99, 255, 0.8)'
                ],
                pointRadius: 0,
                spanGaps: false,
                borderColor: 'rgba(0, 99, 255, 1)',
                // pointBorderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                fill: true
            },
        ]
    };

    rewardGraphOptions = {
        title: {
            display: true,
            text: "Reward"
        },
        aspectRatio: 1.25,
        scales: {
            yAxes: [{
                ticks: {
                    beginAtZero: true
                }
            }]
        }
    };

    completionGraphData = {
        labels: [],
        datasets: [{
            label: 'Eval',
            data: [],
            backgroundColor: [
                'rgba(255, 200, 0, 0.6)'
            ],
            borderColor: 'rgba(255, 160, 0, 1)',
            pointBorderWidth: 0,
            pointRadius: 3,
            // pointBorderColor: 'rgba(255, 0, 0, 1)',
            borderWidth: 1,
            spanGaps: true,
            fill: false
        },
            {
                label: 'Training',
                data: [],
                backgroundColor: [
                    'rgba(0, 255, 128, 0.6)'
                ],
                pointRadius: 0
                // borderColor: 'rgba(0, 99, 255, 1)',
                // pointBorderColor: 'rgba(54, 162, 235, 1)',
                // borderWidth: 1
            },
        ]
    };

    completionGraphOptions = {
        title: {
            display: true,
            text: "Completion %"
        },
        aspectRatio: 1.25,
        scales: {
            yAxes: [{
                scaleLabel: {
                    display: true
                },
                ticks: {
                    beginAtZero: true
                }
            }]
        }
    };


    rewardGraph = new Chart(rewardGraphCanvas, {
        type: 'line',
        data: rewardGraphData,
        options: rewardGraphOptions
    });

    completionGraph = new Chart(completionGraphCanvas, {
        type: 'line',
        data: completionGraphData,
        options: completionGraphOptions
    });

    updateGraphs();
    setInterval(updateGraphs, 10000);
}

function updateGraphs() {
    if (systemState != "running") {
        console.log("Not running yet so not updating graphs");
        return 0
    }
    console.log("Starting data update from episode " + lastMetricsEpisode);
    $.get("/metrics?from_episode=" + lastMetricsEpisode)
        .done(function (data) {
            let sumReward = 0;
            let sumCompletion = 0;
            let evalCount = 0;
            let episode = 0;
            let iteration = 0;
            let phase = null;

            data.forEach(function (metric) {
                if (metric['phase'] == "training") {
                    console.log("TRAIN: " + metric['episode'] + " Reward: " + metric['reward_score'] + " Complete: " + metric['completion_percentage']);

                    if (lastPhase == "evaluation") {
                        // Calculate eval average and update graph
                        if (evalCount > 0) {
                            let averageReward = sumReward / evalCount;
                            let averageCompletion = sumCompletion / evalCount;

                            rewardGraph.data.labels.push(episode);
                            rewardGraph.data.datasets[0].data.push(averageReward);
                            rewardGraph.data.datasets[1].data.push(null);
                            rewardGraph.update();

                            completionGraph.data.labels.push(episode);
                            completionGraph.data.datasets[0].data.push(averageCompletion);
                            completionGraph.data.datasets[1].data.push(null);
                            completionGraph.update();

                            console.log("PLOTTING: Episode: " + episode + " Reward: " + averageReward);
                            sumReward = 0;
                            sumCompletion = 0;
                            evalCount = 0;
                        }
                    }


                    rewardGraph.data.labels.push(metric['episode']);
                    rewardGraph.data.datasets[0].data.push(null);
                    rewardGraph.data.datasets[1].data.push(metric['reward_score']);
                    rewardGraph.update();

                    completionGraph.data.labels.push(metric['episode']);
                    completionGraph.data.datasets[0].data.push(null);
                    completionGraph.data.datasets[1].data.push(metric['completion_percentage']);
                    completionGraph.update();

                    lastPhase = "training";


                }
                if (metric['phase'] == "evaluation") {

                    if (lastPhase == "training") {
                        // start new eval cycle
                        sumReward = 0;
                        sumCompletion = 0;
                        evalCount = 0;
                    }

                    sumReward += metric['reward_score'];
                    sumCompletion += metric['completion_percentage'];
                    evalCount++;

                    console.log("EVAL: " + metric['episode'] + " Reward: " + metric['reward_score'] + " Complete: " + metric['completion_percentage']);
                    lastPhase = "evaluation";
                }

                if (metric['episode'] > lastMetricsEpisode) lastMetricsEpisode = metric['episode'];
                episode = metric['episode'];
                phase = metric['phase'];

            });

            if (phase) {
                $('#sessionEpisode').html(episode);
                $('#sessionPhase').html(phase);

            }


        })
        .fail(function () {
            console.log("GET /metrics error");
        });


}