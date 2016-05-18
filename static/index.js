function redirect(url) {
    document.location = url;
}

function printError(msg) {
    var input = $('#inputUser');
    console.log(msg);
    input.popover({
        trigger: 'manual',
        content: msg
    });
    input.attr('data-content', msg);
    var popover = input.data('bs.popover');
    popover.setContent();
    popover.$tip.addClass(popover.options.placement);
    input.popover('show');
}

// $('#loginModal').modal('show');
$(".index-modal-content").show();
$(".progress-modal-content").hide();

var inputUser = $("#inputUser");

inputUser.on('input', function () {
    $(".input-group").removeClass("has-error has-success");
    $(this).popover('hide');
});

if (username != "ADMIN") {
    inputUser.val(username);
}

$("#getStats").click(function() {
    // redirect(urlGet + $("#inputUser").val());$(".input-group").addClass("has-error");

    var username = $("#inputUser").val();
    if (username == '') {
        $(".input-group").addClass("has-error");
        return;
    }

    $(this).attr("disabled", true);
    $(this).text("Verification...");
    //Starting SSE protocol



    var source = new EventSource("/process/" + username);

    source.addEventListener('verification-failed', function(event) {
        source.close();
        $("#getStats").attr("disabled", false).text("Get stats!");
        $(".input-group").addClass("has-error");
        printError(eval(event.data)[0]['message']);
    });

    source.addEventListener('verification-success', function(event) {
        $(".input-group").addClass("has-success");
        $(".index-modal-content").hide();
        $(".progress-modal-content").show();
    });

    source.addEventListener('import-progress', function(event) {
        var data = eval(event.data);
        $('.progress-bar').css('width', data[0].toString()+'%').attr('aria-valuenow', data[0].toString());
        $('#twiCount').text(data[1].toString());
        //Todo: smooth progress bar
        if (data[0]==100) {
            $('#twiCountText').text("Processing tweets...");
        }
    });

    source.addEventListener('processing-failed', function(event) {
        $(".index-modal-content").show();
        $(".progress-modal-content").hide();
        $("#getStats").attr("disabled", false).text("Get stats!");
        $(".input-group").addClass("has-error");
        source.close();
        printError(event.data);
    });

    source.addEventListener('last-item', function(event) {
        source.close();
        redirect(event.data);
    }, false
    );

});