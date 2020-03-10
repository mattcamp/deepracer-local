$(document).ready(function () {
    $('#addJobButton').click(function () {
        addNewJob()
    });

    $('#startStopButton').click(function () {
        startStopTraining()
    });

    updateStatus();
    updateJobTable();
});

function updateStatus() {
    var jqxhr = $.get("/current_job")
        .done(function (data) {
            console.log("GET /current_job success");
            $("#minioStatus").text(data['minio_status']);
            $("#coachStatus").html(data['coach_status']);
            $("#sagemakerStatus").html(data['sagemaker_status'])
            $("#robomakerStatus").html(data['robomaker_status'])
        })
        .fail(function () {
            console.log("GET /current_job error");
        });
}

function addNewJob() {
    console.log("in addNewJob()");
    data = {};
    $("form#newJobForm :input").each(function () {
        var input = $(this);
        data[input.attr('name')] = input.val();
    });
    var jqxhr = $.post("/jobs", data)
        .done(function () {
            console.log("POST /jobs success");
            updateJobTable();
        })
        .fail(function (error) {
            console.log("POST /jobs error");
            console.log(error['responseText']);
        })
}

function updateJobTable() {
    $("#jobQueueTable").find("tr:gt(0)").remove();
    var jqxhr = $.get("/jobs")
        .done(function (data) {
            console.log("GET /jobs success");
            data.forEach(addJobRow);
        })
        .fail(function () {
            console.log("GET /jobs error");
        });
}

function addJobRow(item, index) {
    console.log("In addJobRow");
    console.log(item);
    $('#jobQueueTable tr:last').after('<tr>' +
        '<td>'+item.id+'</td>' +
        '<td>'+item.name+'</td>' +
        '<td>'+item.episodes+'</td>' +
        '<td>'+item.track+'</td>' +
        '<td>'+item.status+'</td>' +
        '<td>'+item.laps_complete+'</td>' +
        '<td>'+item.average_pct_complete+'</td>' +
        '<td>'+item.best_lap_time+'</td>' +
        '<td><button class="btn btn-sm"><i class="fas fa-edit"></i></button><button class="btn btn-sm"><i class="fas fa-trash-alt"></i></button></td>' +
        '</tr>');
  // document.getElementById("demo").innerHTML += index + ":" + item + "<br>";
}

function startStopTraining() {
    console.log("Clicked button");
    data = {
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
    // var jqxhr = $.post("/current_job", data, dataType: "json")
    //     .done(function () {
    //         console.log("POST /current_job success");
    //         updateJobTable();
    //     })
    //     .fail(function (error) {
    //         console.log("POST /current_job error");
    //         console.log(error['responseText']);
    //     })
}