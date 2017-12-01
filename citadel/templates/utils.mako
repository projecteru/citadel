<%!
  from humanize import naturaltime, naturalsize
  from citadel.views.helper import make_kibana_url
%>

<%def name="container_list(containers)">
  <%def name="header()">
    <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
  </%def>

  <table class="table">
    <thead>
      <tr>
        <th><input type="checkbox" id="check-all"></th>
        <th>ID</th>
        <th>Name</th>
        <th>Version</th>
        <th>Location</th>
        <th>Network</th>
        <th>Entrypoint</th>
        <th>Env</th>
        <th>Status</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      % for c in containers:
        <%
          ssh_command_root = "ssh {container.nodename} -t 'sudo docker-enter {container.short_id}'".format(container=c)
          ssh_command_process = "ssh {container.nodename} -t 'sudo docker exec -it {container.short_id} sh'".format(container=c)
        %>
        <tr>
          <td><input name="container-id" type="checkbox" value="${ c.container_id }"></td>
          <td>
            <a href='javascript://'
              data-placement='right'
              data-toggle="popover"
              rel='popover'
              data-html='true'
              data-original-title='钻进去看看'
              data-content="
              % if g.user.privilege:
                <pre><code style='font-size:70%;white-space:nowrap' >${ ssh_command_root }</code><br><code style='font-size:70%;white-space:nowrap' >${ ssh_command_process }</code></pre>
              % endif
              <a href='${ make_kibana_url(appname=c.appname, ident=c.ident) }' target='_blank'><span class='label label-info'>日志</span></a>
              <a href='http://dashboard.ricebook.net/dashboard/db/eru-apps?var-app=${ c.appname }&var-version=${ c.short_sha }&var-entry=${ c.entrypoint }&var-container_id=${ c.short_id }' target='_blank'><span class='label label-info'>监控</span></a>
              ">
              ${ c.short_id }
            </a>
          </td>
          <td>
            <span data-toggle="tooltip" data-html="true" data-placement="top" title="
              <p>${ naturaltime(c.created) }</p>
              <p>CPU: ${ c.cpu_quota or u'0 (共享)'}</p>
              <p>Memory: ${ naturalsize(c.memory, binary=True) }</p>
              ">
              <a href="${ url_for("app.app", name=c.appname) }" target="_blank">${ c.appname }</a> / ${ c.ident }
            </span>
          </td>
          <td><a href="${ url_for('app.release', name=c.appname, sha=c.sha) }" target="_blank">${ c.short_sha }</a></td>
          <td>
            <a href='javascript://'
              data-placement='right'
              data-toggle="popover"
              rel='popover'
              data-html='true'
              data-content="
              <pre><code style='font-size:70%;white-space:nowrap' > ssh ${ c.nodename } -t 'sudo su'</code></pre>
              <a href='http://dashboard.ricebook.net/dashboard/db/servers?var-hostname=${ c.nodename }' target='_blank'><span class='label label-info'>host监控</span></a>
              <a href='${ url_for('admin.node', podname=c.podname, nodename=c.nodename) }' target='_blank'><span class='label label-info'>这台机还有啥</span></a>
              ">
              ${ c.podname }: ${ c.nodename }
            </a>
          </td>
          <td>
            % if c.get_ips():
              % for n in c.get_ips():
                <span class="block-span">${ n }</span>
              % endfor
            % else:
              host / none
            % endif
          </td>
          <td>${ c.entrypoint }</td>
          <td>${ c.envname }</td>
          <td>
            <% status = c.status() %>
            % if status == 'removing':
              <span title="删不掉稍等重试，再不行才联系平台" class="label label-warning">删除中</span>
            % elif status == 'sick':
              <span class="label label-warning" title="有可能是容器在初始化，也有可能是跑死了">有病</span>
            % elif status == 'debug':
              <span class="label label-warning" title="调试完成后请删除">调试</span>
            % else:
              <span class="label label-${ 'success' if status == 'running' else 'danger' }">
                % if status == 'running':
                  运行
                % elif c.info.get('State', {}).get('OOMKilled'):
                  OOM
                % else:
                  挂了
                % endif
              </span>
            % endif
          </td>
          <td>
            <a name="delete-container" class="btn btn-xs btn-warning" href="#" data-id="${ c.container_id }"><span class="fui-trash"></span></a>
            % if status != 'debug':
              <a title="标记为 debug，从 ELB 上下线，不可撤销" name="debug-container" class="btn btn-xs btn-warning" href="#" data-id="${ c.container_id }">🕷</a>
            % endif
          </td>
        </tr>
      % endfor
    </tbody>
  </table>

  <button name="delete-all" class="btn btn-warning pull-right"><span class="fui-trash"></span> Delete Chosen</button>
  ${ caller.body() }

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

    $('a[name=debug-container]').click(function(e){
      e.preventDefault();
      var self = $(this);
      var containerId = self.data('id');
      var url = '/ajax/debug-container';
      var data = {container_id: containerId}
      $.ajax({
        url: url,
        dataType: 'json',
        type: 'post',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(data, textStatus, jQxhr){
          console.log('Debug container got response: ', data);
          location.reload();
        },
        error: function(jqXhr, textStatus, errorThrown){
          console.log('Debug container got error: ', jqXhr, textStatus, errorThrown);
          alert(jqXhr.responseText);
        }
      })
    });

    $('a[name=delete-container]').click(function(e){
      if (!confirm('确定删除?')) {
        return;
      }
      e.preventDefault();
      var self = $(this);
      var containerId = self.data('id');
      var url = '/ajax/rmcontainer';
      var data = {container_id: containerId}
      $.ajax({
        url: url,
        dataType: 'json',
        type: 'post',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(data, textStatus, jQxhr){
          console.log('Remove container got response: ', data);
          location.reload();
        },
        error: function(jqXhr, textStatus, errorThrown){
          console.log('Remove container got error: ', jqXhr, textStatus, errorThrown);
          alert(jqXhr.responseText);
        }
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
      var data = {};
      var url = '/ajax/rmcontainer';
      $.each($('input[name=container-id]:checked'), function(){
        ids.push($(this).val());
      });
      data.container_id = ids;

      $.ajax({
        url: url,
        dataType: 'json',
        type: 'post',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(data, textStatus, jQxhr){
          console.log('Remove container got response: ', data);
          location.reload();
        },
        error: function(jqXhr, textStatus, errorThrown){
          console.log('Remove container got error: ', jqXhr, textStatus, errorThrown);
          alert(jqXhr.responseText);
        }
      })

    });
  </script>
</%def>

<%def name="release_list(releases, app)">
  <table class="table">
    <thead>
      <tr>
        <th>Version</th>
        <th>Created</th>
        <th>Author</th>
        <th>Branch</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      % for release in releases:
        <tr>
          <td>
            <a href='javascript://'
              data-placement='right'
              data-toggle="popover"
              rel='popover'
              data-html='true'
              data-content="
              <a href='${ url_for('app.release', name=release.appname, sha=release.sha) }'>详情</a>
              ">
              ${ release.sha[:7] }
            </a>
          </td>
          <td>${ naturaltime(release.created) }</td>
          <td class="col-sm-6" style="font-size:70%">
            ${ release.author }: ${ release.commit_message }
          </td>
          <td>
            <span class='label label-info'>
              ${ release.branch }
            </span>
          </td>
          <td>
            % if release.raw:
              <a class="btn btn-xs btn-success" href="${ url_for('app.release', name=release.appname, sha=release.sha) }#add">
                <span class="fui-plus"></span> Add Raw Container
              </a>
            % elif not release.image:
              <a class="btn btn-xs btn-success disabled" href="#">
                <span class="fui-time" ></span> Building...
              </a>
            % else:
              <a class="btn btn-xs btn-success" href="${ url_for('app.release', name=release.appname, sha=release.sha) }#add">
                <span class="fui-plus"></span> Add Container
              </a>
            % endif
            % if release.get_container_list():
              <img style="height: 1em;" src="http://pics.sc.chinaz.com/Files/pic/faces/3709/7.gif">
            % else:
              <a id="delete" class="btn btn-xs btn-warning" data-release-id="${ release.short_sha }" data-delete-url="${ url_for('app.release', name=release.appname, sha=release.sha) }" ><span class="fui-trash"></span></a>
            % endif
          </td>
        </tr>
      % endfor
    </tbody>
  </table>

  <script>
    $('a#delete').click(function (){
      var self = $(this);
      $.ajax({
        url: self.data('delete-url'),
        type: "DELETE",
        success: function(r) {
          console.log(r);
          location.reload();
        },
        error: function(jqXhr, textStatus, errorThrown){
        console.log('Delete release git got error:', jqXhr, textStatus, errorThrown);
        alert(jqXhr.responseText);
        }
      });
    });

  </script>

</%def>

<%def name="panel(panel_class='info')">
  <div class="panel panel-${ panel_class }">
    <div class="panel-heading">
      ${ caller.header() }
    </div>
    <div class="panel-body">
      ${ caller.body() }
    </div>
  </div>
</%def>

<%def name="modal(id, role='dialog', dialog_class='')">
  <div class="modal fade" role="${ role }" id="${ id }">
    <div class="modal-dialog ${ dialog_class }">
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
  <div>
    <ul class="pagination">
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
