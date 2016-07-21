<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Base Image List</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Images</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>URL</th>
          <th>Comment</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        % for image in images:
          <tr>
            <td>${ image.url }</td>
            <td>${ image.comment }</td>
            <td>
              <a class="btn btn-xs btn-warning" href="#" data-url="${ image.url }">
                <span class="fui-trash"></span> Remove
              </a>
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  <div class="col-md-8 col-md-offset-2">
    <form class="form-horizontal" action="${ url_for('admin.images') }" method="POST">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Image URL</label>
        <div class="col-sm-10"><input class="form-control" type="text" name="url"></div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Comment</label>
        <div class="col-sm-10"><input class="form-control" type="text" name="comment"></div>
      </div>
      <div class="form-group">
        <div class="col-sm-10 col-sm-offset-2">
          <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
        </div>
      </div>
    </form>
  </div>
</%block>

<%def name="bottom_script()">
  <script>
    $('a.btn').click(function(e){
      e.preventDefault();
      if (!confirm('确认删除')) {
        return;
      }
      var self = $(this);
      var url = '/ajax/admin/delete-image';
      var data = self.data('url');
      $.post(url, {url: data}, function(){
        self.parent().parent().remove();
      });
    }) 
  </script>
</%def>
