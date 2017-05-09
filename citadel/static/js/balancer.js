;(function($){

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
