consult_input:-
    repeat,
    current_input(H),
    read(H, X),
    amzi_system:exp$term(X, XE),
    amzi_system:do$cons(XE), !.
    
reconsult_input:-
    amzi_system:sys$abolish('{sys}done$'/1),
    repeat,
    current_input(H),
    read(H, X),
    amzi_system:exp$term(X, XE),
    amzi_system:check$term(XE),
    amzi_system:do$recons(XE), !.