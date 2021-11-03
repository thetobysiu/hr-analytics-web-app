FROM #/base-images/alpine:latest as builder
RUN apk add --no-cache \
        --virtual=.build-dependencies \
        g++ gfortran file binutils \
        musl-dev python3-dev py3-pip openblas-dev && \
    apk add libstdc++ openblas && \
    \
    ln -s locale.h /usr/include/xlocale.h && \
    \
    pip3 install --upgrade pip && pip3 install --user pandas flask

FROM #/base-images/alpine:latest as app
RUN apk add --no-cache python3
COPY --from=builder /usr/lib/libopenblas.so.3 /usr/lib/libgfortran.so.5 /usr/lib/libquadmath.so.0 /usr/lib/libgcc_s.so.1 /usr/lib/libstdc++.so.6 /usr/lib/
COPY --from=builder /root/.local /root/.local
COPY ./app /app
WORKDIR /app
ENV PATH=/root/.local/bin:$PATH
EXPOSE 5000
ENTRYPOINT python3 main.py
