;(function($){

  $('select[name=appname]').change(function(){
    var appname = $(this).val();
    var url = '/ajax/app/{appname}/online-entrypoints'.replace('{appname}', appname);
    var podUrl = '/ajax/app/{appname}/online-pods'.replace('{appname}', appname);

    $.get(url, {}, function(r){
      var ep = $('select[name=entrypoint]').html('');
      $.each(r, function(index, data){
        ep.append($('<option>').val(data).text(data));
      })
      ep.append($('<option>').val('_all').text('_all'));
    });
    $.get(podUrl, {}, function(r){
      var ep = $('select[name=podname]').html('');
      $.each(r, function(index, data){
        ep.append($('<option>').val(data).text(data));
      })
    });
  });

  $('a[name=delete-rule]').click(function(e){
    e.preventDefault();
    var self = $(this);
    var domain = self.data('rule-domain');
    if (!confirm('确定删除' + domain + '?')) {
      return;
    }
    var url = '/ajax/' + self.data('elbname') + '/delete';
    var data = {domain: domain}
    $.ajax({
      url: url,
      dataType: 'json',
      type: 'post',
      contentType: 'application/json',
      data: JSON.stringify(data),
      success: function(data, textStatus, jQxhr){
        console.log('Delete rule got response: ', data);
        location.reload();
      },
      error: function(jqXhr, textStatus, errorThrown){
        console.log('Delete rule got error: ', jqXhr, textStatus, errorThrown);
        alert(jqXhr.responseText);
      }
    })
  });

})(jQuery);
