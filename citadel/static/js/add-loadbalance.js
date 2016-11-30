;(function($){

$('#add-modal').click(function(){
  $('#add-load-balance').modal('toggle');
});

$('select[name=releaseid]').change(function(){
  var releaseId = $(this).val();
  var ep = $('select[name=entrypoint]');
  var url = '/ajax/release/' + releaseId + '/entrypoints';
  $.get(url, {}, function(r){
    ep.html('');
    $.each(r, function(index, data){
      ep.append($('<option>').val(data).text(data));
    });
  });
});

$('#add-load-balance-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/loadbalance';
  var data = {};

  data.releaseid = $('select[name=releaseid]').val();
  data.nodename = $('select[name=node]').val();
  data.entrypoint = $('select[name=entrypoint]').val();
  data.cpu = $('input[name=cpu]').val() || '1';
  data.comment = $('input[name=comment]').val() || '';
  data.envname = $('select[name=envname]').val() || '';

  console.log('ELB deploy args:', data);
  $.ajax({
    url: url,
    dataType: 'json',
    type: 'post',
    contentType: 'application/json',
    data: JSON.stringify(data),
    success: function(data, textStatus, jQxhr){
      console.log('Add loadbalance got response: ', data);
      location.reload();
    },
    error: function(jqXhr, textStatus, errorThrown){
      console.log('Add loadbalance got error: ', jqXhr, textStatus, errorThrown);
      alert(jqXhr.responseText);
    }
  })

});

$('a[name=delete-balancer]').click(function(e){
  e.preventDefault();
  if (!confirm('确认删除?')) {
    return;
  }
  var self = $(this);
  var url = '/ajax/loadbalance/{id}/remove'.replace('{id}', self.data('id'));

  $.ajax({
    url: url,
    dataType: 'json',
    type: 'post',
    contentType: 'application/json',
    data: JSON.stringify({}),
    success: function(data, textStatus, jQxhr){
      console.log('Remove loadbalance got response: ', data);
      location.reload();
    },
    error: function(jqXhr, textStatus, errorThrown){
      console.log('Remove loadbalance got error: ', jqXhr, textStatus, errorThrown);
      alert(jqXhr.responseText);
    }
  })

});

})(jQuery);
