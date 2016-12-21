<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ app.name }
</%def>

<%def name="more_css()">
  .block-span { display: block; }
</%def>

<%!
  from datetime import datetime
%>

<%block name="main">

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">App
        <a href="${ url_for('app.app_env', name=app.name) }" class="btn-xs" target="_blank">
          • Environment Variables
        </a>
        <a href="${ url_for('app.app_permitted_users', name=app.name) }" class="btn-xs" target="_blank">
          • Permitted Users
        </a>
      </h3>
    </%def>
    <h4>${ app.name }</h4>
    <p>${ app.gitlab_project.as_dict()['description'] }</p>
    <h5>Log</h5>
    <p>Kibana 看 log 其实很好用的，如果点进去看不见 log，请在右上角修改一下时间范围。建议自己探索一下界面，实在搞不懂请找 @Dante </p>
    <ul class="list-group">
      % if releases:
        % for entry in releases[0].entrypoints.keys():
          <li class="list-group-item"><a target="_blank" href="http://kibana.ricebook.net/app/logtrail#/?q=name:${ app.name }%20%26%26%20entrypoint:${ entry }&h=All&t=Now&_g=()">${ entry }</a></li>
        % endfor
      % endif
      <li class="list-group-item">线上 log 也可以 terminal 看（没权限去 #sa-online 申请）：<pre>ssh c2-eru-2 -t 'tail -F /mnt/mfs/logs/eru2/[APPNAME]/[ENTRYPOINT]/[DATE]/[HOUR] -n 100'</pre></li>
      <li class="list-group-item">Debug log 在部署以后实时显示的，但是有微小几率丢失开头的几行，可以用 terminal 看：<pre>ssh c2-eru-2 -t 'tail -F /mnt/mfs/logs/heka/debug-output.log -n 100 | ag ${ app.name }'</pre></li>
    </ul>
    <h5>域名</h5>
    <ul class="list-group">
      % for rule in app.get_associated_elb_rules():
        <li class="list-group-item"><a target="_blank" href="${ url_for('loadbalance.elb', name=rule.elbname) }#${ rule.domain }">${ rule.domain }</a></li>
      % endfor
    </ul>
    <button id="delete-app" class="btn btn-warning pull-right" data-appname="${ app.name }"><span class="fui-trash"></span> Delete App</button>
  </%utils:panel>

  <%utils:panel>
    <%def name="header()">
      <h3 class="panel-title">Latest Versions
      </h3>
    </%def>
    ${ utils.release_list(releases, app) }
  </%utils:panel>

  <%utils:panel>

    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>

    <%utils:container_list containers="${ containers }">
      <button name="upgrade-container" class="btn btn-primary pull-left" data-toggle="modal" data-target="#upgrade-container-modal"><span class="fui-apple"></span>升级或者换新</button>
    </%utils:container_list>

  </%utils:panel>

  <%call expr="utils.modal('upgrade-container-modal')">
    <%def name="header()">
      <h3 class="modal-title">Upgrade Container</h3>
    </%def>

    <form id="upgrade-container-form" class="form-horizontal" action="">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Release</label>
        <div class="col-sm-10">
          <select name="release" class="form-control">
            % for release in releases:
              % if release.image:
                <option value="${ release.sha }" >${ release.short_sha }</option>
              % else:
                <option value="${ release.sha }" disabled>${ release.short_sha }</option>
              % endif
            % endfor
          </select>
        </div>
      </div>
    </form>

    <%def name="footer()">
      <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
      <button class="btn btn-info" id="upgrade-container-button"><span class="fui-apple"></span>Upgrade</button>
    </%def>
  </%call>

  <%call expr="utils.modal('upgrade-container-progress', dialog_class='modal-lg')">
    <%def name="header()">
      <h3 class="modal-title">Upgrading...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <pre id="upgrade-container-pre"></pre>

  </%call>

  <script>
    $('button[id=upgrade-container-button]').click(function(e){
      e.preventDefault();
      if (!$('input[name=container-id]:checked').length) {
        return;
      }

      var data = {};
      var container_ids = [];
      data.sha = $('select[name=release]').val();
      $.each($('input[name=container-id]:checked'), function(){
        container_ids.push($(this).val());
      })
      data.container_ids = container_ids;

      $('#upgrade-container-modal').modal('hide');
      $('#upgrade-container-progress').modal('show');

      var logDisplay = $('#upgrade-container-pre');
      var success = true;
      oboe({url: "${ url_for('ajax.upgrade_containers') }", method: 'POST', body: data})
        .done(function(r) {
          console.log(r);
          if (r.error) {
            console.log('Upgrade Container got error', r);
            success = false;
            $('#upgrade-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
            logDisplay.append(r.error + '\n');
          } else if (r.type == 'sentence') {
            logDisplay.append(r.message + '\n');
          } else {
            logDisplay.append(JSON.stringify(r) + '\n');
          }
          $(window).scrollTop($(document).height() - $(window).height());
        }).fail(function(r) {
          logDisplay.append(JSON.stringify(r) + '\n');
          $('#upgrade-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
          console.log(r);
        })
        .on('end', function() {
          console.log('Got end signal, success:', success);
          if (success == true) {
            window.location.href = window.location.href.replace(/#\w+/g, '');
          } else {
          $('#upgrade-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
          }
        })
    })

    $('button#delete-app').click(function (){
      var self = $(this);
      if (!confirm('确定删除' + self.data('appname') + '?')) { return; }
      $.ajax({
        url: "${ url_for('app.app', name=app.name) }",
        type: 'DELETE',
        success: function(r) {
          console.log(r);
          if (r.status == 200) {
            location.href = "${ url_for('app.index') }";
          }
        },
        error: function(r) {
          console.log(r);
          alert(JSON.stringify(r.responseJSON));
        }
      })
    })
  </script>

</%block>
