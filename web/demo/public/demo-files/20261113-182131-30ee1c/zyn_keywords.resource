*** Settings ***
Documentation    Keywords the Zyn-generated suite uses. Zyn prototype.
...              Map each keyword to your bench library (CAN interface, SIL or HIL).
...              Until you do, every keyword fails, so no test can pass by accident.

*** Keywords ***
Set Signal
    [Arguments]    ${signal}    ${value}
    Fail    Not mapped to a bench: Set Signal ${signal} ${value}

Stop Message
    [Arguments]    ${message}
    Fail    Not mapped to a bench: Stop Message ${message}

Expect Within
    [Arguments]    ${signal}    ${value}    ${ms}
    Fail    Not mapped to a bench: Expect Within ${signal} ${value} ${ms}

Expect For
    [Arguments]    ${signal}    ${value}    ${ms}
    Fail    Not mapped to a bench: Expect For ${signal} ${value} ${ms}

Expect Absent
    [Arguments]    ${signal}    ${value}    ${ms}
    Fail    Not mapped to a bench: Expect Absent ${signal} ${value} ${ms}

Expect In Range After
    [Arguments]    ${signal}    ${low}    ${high}    ${ms}
    Fail    Not mapped to a bench: Expect In Range After ${signal} ${low} ${high} ${ms}

Expect Period
    [Arguments]    ${message}    ${period_ms}    ${tolerance_ms}    ${count}
    Fail    Not mapped to a bench: Expect Period ${message} ${period_ms}
