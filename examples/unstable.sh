# @TEST-EXEC: echo $(($ones+$RANDOM/2**14)) >output
# @TEST-EXEC: btest-diff output