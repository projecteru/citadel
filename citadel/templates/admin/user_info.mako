<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">User ${ user.name }</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Apps for ${ user.name } / ${ user.real_name }</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Git</th>
          <th>Update</th>
          <th>Operations</th>
        </tr>
      </thead>
      <tbody>
        % for app in apps:
          <tr>
            <td>${ app.name }</td>
            <td>${ app.git }</td>
            <td>${ app.updated }</td>
            <td>
              <a class="btn btn-xs btn-warning" href="#" data-user-id="${ user.id }" data-name="${ app.name }">
                <span class="fui-cross"></span> Revoke
              </a>
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  <div class="col-md-8 col-md-offset-2">
    <form class="form-horizontal" action="${ url_for('admin.user_info', identifier=user.id) }" method="POST">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">App Name</label>
        <div class="col-sm-10">
          <select id="" class="form-control" name="name">
            % for app in all_apps:
              <option value="${ app.name }">${ app.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <div class="col-sm-10 col-sm-offset-2">
          <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Grant</button>
        </div>
      </div>
    </form>
  </div>

</%block>

<%def name="bottom_script()">
  <script>
    $('a.btn').click(function(e){
      e.preventDefault();
      if (!confirm('确认撤销?')) {
        return;
      }
      var self = $(this);
      var url = '/ajax/admin/revoke-app';
      var name = self.data('name');
      var id = self.data('user-id')
      $.post(url, {user_id: id, name: name}, function(){
        self.parent().parent().remove();
      });
    });
  </script>
</%def>
