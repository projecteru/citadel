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
  from citadel.libs.utils import shorten_sentence
  from citadel.views.helper import make_kibana_url
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
    <h5>日志 & 监控</h5>
    <ul class="list-group">
      % if releases:
        % for entry in releases[0].entrypoints.keys():
          <li class="list-group-item">
            <a href='javascript://'
              data-placement='right'
              data-toggle="popover"
              rel='popover'
              data-html='true'
              data-content="
              <a href='${ make_kibana_url(appname=app.name, entrypoint=entry) }' target='_blank'><span class='label label-info'>日志</span></a>
              <a href='http://dashboard.ricebook.net/dashboard/db/eru-apps-aggregation?var-app=${ app.name }&var-entry=${ entry }' target='_blank'><span class='label label-info'>监控</span></a>
              ">
              ${ entry }
            </a>
          </li>
        % endfor
      % endif
    </ul>
    <h5>域名</h5>
    <p>操作域名前请务必详读<a href="http://platform.docs.ricebook.net/citadel/docs/user-docs/setup.html#4-绑定域名" target="_blank">文档</a></p>
    <ul class="list-group">
      % for rule in app.get_associated_elb_rules(g.zone):
        <li class="list-group-item">
        <a target="_blank" href="${ url_for('loadbalance.elb', name=rule.elbname) }#${ rule.domain }">${ rule.domain }</a>
        <a name="delete-rule" class="btn btn-xs btn-warning" data-rule-domain="${ rule.domain }" data-elbname="${ rule.elbname }"><span class="fui-trash"></span></a>
        </li>
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
                <option value="${ release.sha }" >${ release.short_sha } (${ release.branch }): ${ shorten_sentence(release.commit_message) }...</option>
              % else:
                <option value="${ release.sha }" disabled>${ release.short_sha } (${ release.branch }): ${ shorten_sentence(release.commit_message) }...</option>
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

  <script src="/citadel/static/js/balancer.js" type="text/javascript"></script>
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
