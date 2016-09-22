;(function($){

$(document).ready(function(){
  var anchor = window.location.hash;
  if (anchor === '#add') {
    $('#add-container-modal').modal('show');
  }
});

$('#add-container-form select[name=pod]').change(function(){
  var pod = $(this).val();
  var node_selection = $('select[name=node]');
  var get_nodes_url = '/ajax/pod/' + pod + '/nodes';
  $.get(get_nodes_url, {}, function(r){
    node_selection.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    for (var i=0; i<r.length; i++) {
      node_selection.append($('<option>').val(r[i].name).text(r[i].name + ' - ' + r[i].ip));
    }
  });
  var network_checkboxes = $('#network-checkbox');
  var get_networks_url = '/api/v1/pod/' + pod + '/networks';
  $.get(get_networks_url, {}, function(r){
    network_checkboxes.html("")
    for (var i=0; i<r.length; i++) {
      network_checkboxes.append('<label class="checkbox"><input type="checkbox" name="network" value="' + r[i].name + '">' + r[i].name + ' - ' + r[i].subnets + '</label>');
    }
  });
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

  if ($('div.active #add-container-form').length) {
    data.envname = $('div.active #add-container-form select[name=envname]').val() || '';
    data.podname = $('div.active #add-container-form select[name=pod]').val();
    data.nodename = $('div.active #add-container-form select[name=node]').val();
    data.entrypoint = $('div.active #add-container-form select[name=entrypoint]').val();
    data.count = $('div.active #add-container-form input[name=count]').val() || '1';
    data.envs = $('div.active #add-container-form input[name=envs]').val();
    data.networks = networks;
    data.raw = $('div.active #add-container-form input[name=raw]:checked').length;
  } else {
    data.envname = $('#add-container-form select[name=envname]').val() || '';
    data.podname = $('#add-container-form select[name=pod]').val();
    data.nodename = $('#add-container-form select[name=node]').val();
    data.entrypoint = $('#add-container-form select[name=entrypoint]').val();
    data.count = $('#add-container-form input[name=count]').val() || '1';
    data.envs = $('#add-container-form input[name=envs]').val();
    data.networks = networks;
    data.raw = $('#add-container-form input[name=raw]:checked').length;
  }

  console.log(data);
  var progressBar = $('div.progress-bar');

  $('#add-container-modal').modal('hide');
  $('#container-progress').modal('show');
  progressBar.width('0').animate({width: '100%'}, 10000);
  $.post(url, data, function(r){
    if (r.error !== null) {
      alert(r.error);
      return;
    }
    $('#container-progress').modal('hide');
    window.location.href = window.location.href.replace(/#\w+/g, '');
  });
});

})(jQuery);
