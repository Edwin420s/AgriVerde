#ifndef IRRIGATION_H
#define IRRIGATION_H

void setupIrrigation();
void updateIrrigation();
void stopPump();

extern bool isPumpRunning;
extern unsigned long pumpCurrentRuntime;

#endif
