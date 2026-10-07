// SPDX-License-Identifier: MIT
// Read-only module loading smoke test. Never clicks controls or edits settings.
#include <QApplication>
#include <QPluginLoader>
#include <QTimer>
#include <QListWidget>
#include <QCheckBox>
#include <KCModule>
#include <KPluginFactory>
#include <cstdio>
int main(int argc, char **argv) {
    QApplication app(argc, argv);
    if (argc < 2) return 2;
    QPluginLoader loader(QString::fromLocal8Bit(argv[1]));
    auto factory = qobject_cast<KPluginFactory *>(loader.instance());
    if (!factory) { fprintf(stderr,"%s\n",qPrintable(loader.errorString())); return 3; }
    auto module = factory->create<KCModule>();
    if (!module) return 4;
    module->widget()->resize(680,650);
    module->widget()->show();
    QTimer::singleShot(4000, &app, [&] {
        auto toggle = module->widget()->findChild<QCheckBox *>();
        auto list = module->widget()->findChild<QListWidget *>();
        bool ok = toggle && toggle->isChecked() && list && list->count() > 0;
        if (argc > 2) module->widget()->grab().save(QString::fromLocal8Bit(argv[2]));
        printf("shell enabled=%d; selectable plugins=%d\n", toggle && toggle->isChecked(), list ? list->count() : -1);
        app.exit(ok ? 0 : 5);
    });
    return app.exec();
}
