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
  var hosts = $('select[name=node]');
  var url = '/ajax/pod/' + pod + '/nodes';
  $.get(url, {}, function(r){
    hosts.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    for (var i=0; i<r.length; i++) {
      hosts.append($('<option>').val(r[i].name).text(r[i].name + ' - ' + r[i].ip));
    }
  });
});

$(document).ajaxStart(function(){
  var progressBar = $('div.progress-bar');

  $('#add-container-modal').modal('hide');
  $('#container-progress').modal('show');
  progressBar.width('0').animate({width: '100%'}, 10000);
}).ajaxStop(function(){
  $('#container-progress').modal('hide');
});

$('#add-container-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/release/{releaseId}/deploy';
  var data = {};
  var networks = [];
  var releaseId = $('#add-container-form input[name=release]').data('id');

  url = url.replace('{releaseId}', releaseId);

  var ns = $('#add-container-form input[name=network]:checked');
  for (var i=0; i<ns.length; i++) {
    networks.push($(ns[i]).val());
  }

  data.envname = $('#add-container-form select[name=envname]').val() || '';
  data.podname = $('#add-container-form select[name=pod]').val();
  data.nodename = $('#add-container-form select[name=node]').val();
  data.entrypoint = $('#add-container-form select[name=entrypoint]').val();
  data.cpu = $('#add-container-form input[name=cpu]').val() || '1';
  data.count = $('#add-container-form input[name=count]').val() || '1';
  data.envs = $('#add-container-form input[name=envs]').val();
  data.networks = networks;
  data.raw = $('#add-container-form input[name=raw]:checked').length;

  console.log(data);
  $.post(url, data, function(r){
    if (r.error !== null) {
      alert(r.error);
      return;
    }
    location.reload();
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
