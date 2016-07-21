;(function($){

$(document).ready(function(){
  var anchor = window.location.hash;
  if (anchor === '#build') {
    $('#build-image-modal').modal('show');
  } else if (anchor === '#add') {
    $('#add-container-modal').modal('show');
  }
});

$('#add-container-form select[name=pod]').change(function(){
  var pod = $(this).val();
  var hosts = $('select[name=host]');
  var url = '/ajax/pod/' + pod + '/hosts';
  $.get(url, {}, function(r){
    hosts.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    for (var i=0; i<r.length; i++) {
      hosts.append($('<option>').val(r[i].name).text(r[i].name + ' - ' + r[i].ip));
    }
  });
});

$('input[name=private]').change(function(){
  var ncore = $('input[name=ncore]')
  if (!$(this).is(':checked')) {
    ncore.val('0').prop('disabled', true);
    } else {
    ncore.val('1').prop('disabled', false);
  }
});

$('#add-container-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/app/{name}/version/{sha}/container';
  var data = {};
  var networks = [];

  url = url.replace('{name}', $('input[name=name]').val()).replace('{sha}', $('input[name=version]').val());

  var ns = $('#add-container-form input[name=network]:checked');
  for (var i=0; i<ns.length; i++) {
    networks.push($(ns[i]).val());
  }

  data.env = $('#add-container-form select[name=env]').val() || 'prod';
  data.podname = $('#add-container-form select[name=pod]').val();
  data.hostname = $('#add-container-form select[name=host]').val();
  data.entrypoint = $('#add-container-form select[name=entrypoint]').val();
  data.ncore = $('#add-container-form input[name=ncore]').val() || '1';
  data.ncontainer = $('#add-container-form input[name=ncontainer]').val() || '1';
  data.private = $('#add-container-form input[name=private]').is(':checked');
  data.envs = $('#add-container-form input[name=envs]').val();
  data.networks = networks;

  console.log(data);
  $.post(url, data, function(r){
    console.log(r);
    var qts = [];
    $.each(r.tasks, function(index, data){
      qts.push('task=' + data);
    });
    var wsUrl = 'ws://' + location.host + '/websocket/check-container-add?' + qts.join('&');
    var progressBar = $('div.progress-bar');

    $('#add-container-modal').modal('hide');
    $('#add-container-progress').modal('show');
    progressBar.width('0').animate({width: '100%'}, 10000);

    waitForWebsocket(wsUrl, function(e){
      progressBar.width('100%');
      location.reload();
    });
  });
});

$('#build-image-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/app/{name}/version/{sha}/build';
  var data = {};

  url = url.replace('{name}', $('input[name=name]').val()).replace('{sha}', $('input[name=version]').val());

  data.podname = $('#build-image-form select[name=pod]').val();
  data.base = $('#build-image-form select[name=base]').val();

  console.log(data);
  $.post(url, data, function(r){
    console.log(r);

    $('#build-image-modal').modal('hide');
    $('#build-image-progress').modal('show');

    var wsUrl = 'ws://' + location.host + '/websocket/check-build-image?task=' + r.task;
    waitForWebsocket(wsUrl, function(e) {
      if (e.data === 'done') {
        location.reload();
      }
      $('#build-image-pre').append('\n' + e.data);
      $(window).scrollTop($(document).height() - $(window).height());
    });
  });
});

})(jQuery);
