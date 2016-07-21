<%def name="container_list(containers)">
  <table class="table">
    <thead>
      <tr>
        <th><input type="checkbox" id="check-all"></th>
        <th>ID</th>
        <th>Name</th>
        <th>Version</th>
        <th>Host</th>
        <th>Network</th>
        <th>CPU</th>
        <th>Entrypoint</th>
        <th>Env</th>
        <th>Status</th>
        <th>Operation</th>
      </tr>
    </thead>
    <tbody>
      % for c in containers:
        <tr>
          <td><input name="container-id" type="checkbox" value="${ c.short_id }"></td>
          <td>${ c.short_id }</td>
          <td>
            <span data-toggle="tooltip" data-placement="top" title="创建于 ${ c.created }">
              ${ c.appname } / ${ c.ident }
            </span>
          </td>
          <td>${ c.version }</td>
          <td>${ c.host_ip } / ${ c.hostname }</td>
          <td>
            % if c.networks:
              % for n in c.networks:
                <span class="block-span">${ n.vlan_address }</span>
              % endfor
            % else:
              host / none
            % endif
          </td>
          <td>
            % if c.excluded_core_label or c.shared_core_label:
              ${ len(c.excluded_core_label) + float(c.nshare / 10.0) }
            % else:
              0 (共享)
            % endif
          </td>
          <td>${ c.entrypoint }</td>
          <td>${ c.env }</td>
          <td>
            % if c.in_removal:
              <span class="label label-warning">删除中...</span>
            % else:
              <span class="label label-${ 'success' if c.is_alive else 'danger' }">
                ${ u'运行' if c.is_alive else u'挂了' }
              </span>
            % endif
          </td>
          <td>
            <a name="delete-container" class="btn btn-xs btn-warning" href="#" data-id="${ c.container_id }"><span class="fui-trash"></span> Delete</a>
          </td>
        </tr>
      % endfor
    </tbody>
  </table>

  <button name="delete-all" class="btn btn-warning pull-right"><span class="fui-trash"></span> Delete Chosen</button>

  <script>
    $('#check-all').change(function(){
      var checked = this.checked;
      $.each($('input[name=container-id]'), function(){
        this.checked = checked;
      });
    });

    $(function(){
      $('[data-toggle="tooltip"]').tooltip();
    });

    $(document).on('click', 'a[name=delete-container]', function(e){
      if (!confirm('确定删除?')) {
        return;
      }
      e.preventDefault();
      var self = $(this);
      var containerId = self.data('id');
      var url = '/ajax/rmcontainer';
      $.post(url, {container_id: containerId}, function(){
        self.parent().parent().remove();
      })
    });

    $('button[name=delete-all]').click(function(e){
      if (!confirm('确定删除?')) {
        return;
      }
      if (!$('input[name=container-id]:checked').length) {
        return;
      }
      e.preventDefault();
      var ids = [];
      var url = '/ajax/rmcontainer';
      $.each($('input[name=container-id]:checked'), function(){
        ids.push('container_id=' + $(this).val());
      });
      $.post(url, ids.join('&'), function(){
        $.each($('input[name=container-id]:checked'), function(){
          $(this).parent().parent().remove();
        });
      })
    });
  </script>
</%def>

<%def name="version_list(versions, app)">
  <%
    project = app.get_gitlab_project()
  %>
  <table class="table">
    <thead>
      <tr>
        <th>Version</th>
        <th>Created</th>
        <th>Author</th>
        <th>GitLab Link</th>
        <th>Operation</th>
      </tr>
    </thead>
    <tbody>
      % for v in versions:
        <tr>
          <td><a href="${ url_for('app.get_version', name=v.name, sha=v.sha) }">${ v.sha[:7] }</a></td>
          <td>${ v.created }</td>
          <%
            try:
              commit = project.commits.get(v.sha)
              author = commit.author_name
              message = commit.message
            except:
              author = 'unknown'
              message = 'unknown'
          %>
          <td>
            <span data-toggle="tooltip" data-placement="top" title="${ message }">
              ${ author }
            </span>
          </td>
          <td>
            <a href="${ url_for('app.gitlab_url', name=v.name, sha=v.sha) }" target="_blank">${ v.sha[:7] }</a>
          </td>
          <td>
            % if v.image:
              <a class="btn btn-xs btn-success" href="${ url_for('app.get_version', name=v.name, sha=v.sha) }#add">
                <span class="fui-plus"></span> Add Container
              </a>
            % else:
              % if v.build_status == 'waiting':
                <a class="btn btn-xs btn-info" href="${ url_for('app.get_version', name=v.name, sha=v.sha) }#build">
                  <span class="fui-time"></span> Build Image
                </a>
              % elif v.build_status == 'building':
                <a class="btn btn-xs btn-info disabled" href="${ url_for('app.get_version', name=v.name, sha=v.sha) }#build">
                  <span class="fui-time"></span> Building...
                </a>
              % elif v.build_status == 'fail':
                <a class="btn btn-xs btn-danger" href="${ url_for('app.get_version', name=v.name, sha=v.sha) }#build">
                  <span class="fui-time"></span> Failed, rebuild
                </a>
              % endif
            % endif
          </td>
        </tr>
      % endfor
    </tbody>
  </table>
</%def>

<%def name="panel(panel_class='info')">
  <div class="panel panel-${panel_class}">
    <div class="panel-heading">
      ${ caller.header() }
    </div>
    <div class="panel-body">
      ${ caller.body() }
    </div>
  </div>
</%def>

<%def name="modal(id, role='dialog')">
  <div class="modal fade" role="${ role }" id="${ id }">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          ${ caller.header() }
        </div>
        <div class="modal-body">
          ${ caller.body() }
        </div>
        <div class="modal-footer">
          ${ caller.footer() }
        </div>
      </div>
    </div>
  </div>
</%def>

<%def name="paginator(start=None, limit=None)">
  <%
    if start is None:
        start = g.start
    if limit is None:
        limit = g.limit
    cur_page = start // limit + 1
    begin = max(cur_page - 3, 1)
    end = cur_page + 3
    prev = 'disabled' if cur_page <= 1 else ''
    prev_num = max((cur_page - 2) * limit, 0)
  %>
  <div class="pagination">
    <ul>
      <li class="previous ${ prev }">
      <a class="fui-arrow-left" href="${ request.base_url }?start=${ prev_num }&limit=${ limit }"></a>
      </li>
      % for i in range(begin, end):
        <li class="${ 'active' if cur_page == i else '' }">
        <a href="${ request.base_url }?start=${ (i-1)*limit }&limit=${ limit }">${ i }</a>
        </li>
      % endfor
      <li class="next">
      <a class="fui-arrow-right" href="${ request.base_url }?start=${ cur_page*limit }&limit=${ limit }"></a>
      </li>
    </ul>
  </div>
</%def>
