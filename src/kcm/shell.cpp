// SPDX-License-Identifier: MIT
#include <KCModule>
#include <KPluginFactory>
#include <QCheckBox>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QListWidget>
#include <QProcess>
#include <QPushButton>
#include <QTimer>
#include <functional>
#include <QSignalBlocker>
#include <QVBoxLayout>

class ShellSettings : public KCModule {
    Q_OBJECT
public:
    ShellSettings(QObject *parent, const KPluginMetaData &data) : KCModule(parent, data) {
        setButtons(NoAdditionalButton);
        auto layout = new QVBoxLayout(widget());
        auto description = new QLabel(tr("Use the Omarchy shell alongside Plasma. Changes take effect immediately."), widget());
        description->setWordWrap(true);
        layout->addWidget(description);
        toggle = new QCheckBox(tr("Enable Omarchy shell"), widget());
        layout->addWidget(toggle);
        status = new QLabel(widget());
        status->setWordWrap(true);
        layout->addWidget(status);
        layout->addWidget(new QLabel(tr("Widgets and plugins"), widget()));
        plugins = new QListWidget(widget());
        layout->addWidget(plugins);
        auto refresh = new QPushButton(tr("Refresh"), widget());
        layout->addWidget(refresh);
        connect(refresh, &QPushButton::clicked, this, [this] { errorMessage.clear(); load(); });
        connect(toggle, &QCheckBox::clicked, this, [this](bool checked) {
            errorMessage.clear();
            execute(QStringLiteral("/usr/bin/frankenstein"), {QStringLiteral("shell"), checked ? QStringLiteral("on") : QStringLiteral("off")}, [this](bool ok, QByteArray output) {
                if (!ok) errorMessage = tr("Could not change the shell: %1").arg(QString::fromUtf8(output).left(500));
                load();
            });
        });
        connect(plugins, &QListWidget::itemChanged, this, [this](QListWidgetItem *item) {
            errorMessage.clear();
            const auto id = item->data(Qt::UserRole).toString();
            execute(QStringLiteral("/usr/bin/omarchy"), {QStringLiteral("plugin"), item->checkState() == Qt::Checked ? QStringLiteral("enable") : QStringLiteral("disable"), id}, [this](bool ok, QByteArray output) {
                if (!ok) errorMessage = tr("Could not change the widget: %1").arg(QString::fromUtf8(output).left(500));
                load();
            });
        });
        load();
    }
    void load() override {
        if (busy) return;
        execute(QStringLiteral("/usr/bin/frankenstein"), {QStringLiteral("shell"), QStringLiteral("status")}, [this](bool ok, QByteArray output) {
            const bool enabled = output.trimmed() == "active";
            QSignalBlocker blocker(toggle);
            toggle->setChecked(enabled);
            status->setText(ok ? (enabled ? tr("The Omarchy shell is running.") : tr("The Omarchy shell is off. Enable it to configure widgets.")) : tr("Shell integration unavailable: %1").arg(QString::fromUtf8(output).left(500)));
            if (!errorMessage.isEmpty()) status->setText(errorMessage);
            plugins->clear();
            if (!ok || !enabled) return;
            execute(QStringLiteral("/usr/bin/frankenstein"), {QStringLiteral("shell"), QStringLiteral("mode")}, [this](bool modeOk, QByteArray mode) {
                if (!modeOk || mode.trimmed() != "preserve") {
                    status->setText(tr("The filtered Plasma adapter is running. Its widget selection is managed by the Frankenstein profile."));
                    return;
                }
                execute(QStringLiteral("/usr/bin/omarchy"), {QStringLiteral("plugin"), QStringLiteral("list"), QStringLiteral("--json")}, [this](bool listOk, QByteArray output) {
                    QJsonParseError error;
                    auto document = QJsonDocument::fromJson(output, &error);
                    if (!listOk || error.error != QJsonParseError::NoError || !document.isArray()) {
                        status->setText(tr("Could not read widgets. Refresh to try again."));
                        return;
                    }
                    QSignalBlocker blocker(plugins);
                    for (auto entry : document.array()) {
                        auto object = entry.toObject();
                        if (!object.value("canDisable").toBool(true)) continue;
                        auto item = new QListWidgetItem(object.value("name").toString(object.value("id").toString()), plugins);
                        item->setToolTip(object.value("id").toString());
                        item->setData(Qt::UserRole, object.value("id").toString());
                        item->setFlags(item->flags() | Qt::ItemIsUserCheckable);
                        item->setCheckState(object.value("enabled").toBool() ? Qt::Checked : Qt::Unchecked);
                    }
                    plugins->sortItems();
                });
            });
        });
    }
private:
    QCheckBox *toggle;
    QLabel *status;
    QListWidget *plugins;
    bool busy = false;
    QString errorMessage;
    void execute(const QString &program, const QStringList &arguments, std::function<void(bool, QByteArray)> done) {
        if (busy) return;
        busy = true;
        toggle->setEnabled(false);
        plugins->setEnabled(false);
        auto process = new QProcess(this);
        process->setProcessChannelMode(QProcess::MergedChannels);
        auto timer = new QTimer(process);
        timer->setSingleShot(true);
        timer->setInterval(10000);
        connect(timer, &QTimer::timeout, process, &QProcess::kill);
        auto finish = [this, process, done](bool ok) {
            if (process->property("finished").toBool()) return;
            process->setProperty("finished", true);
            auto output = process->readAll().left(131072);
            busy = false;
            toggle->setEnabled(true);
            plugins->setEnabled(true);
            process->deleteLater();
            done(ok, output);
        };
        connect(process, &QProcess::finished, this, [finish](int code, QProcess::ExitStatus exit) { finish(code == 0 && exit == QProcess::NormalExit); });
        connect(process, &QProcess::errorOccurred, this, [finish](QProcess::ProcessError error) { if (error == QProcess::FailedToStart) finish(false); });
        process->start(program, arguments);
        timer->start();
    }
};
K_PLUGIN_CLASS_WITH_JSON(ShellSettings, "shell.json")
#include "shell.moc"
