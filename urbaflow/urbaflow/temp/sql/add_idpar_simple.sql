ALTER TABLE public.parcellaire_france add column idpar_simple text;
update public.parcellaire_france set idpar_simple = right(idpar, length(idpar)-8);